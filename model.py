# In[]
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import xgboost as xgb
import shap
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    mean_squared_error,
    mean_absolute_error,
    r2_score,
    explained_variance_score,
    max_error,
    median_absolute_error
)
from datetime import timedelta
import warnings
warnings.filterwarnings('ignore')
import os
import json

plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial']
plt.rcParams['axes.unicode_minus'] = False

OUTPUT_DIR = 'output'
os.makedirs(OUTPUT_DIR, exist_ok=True)

LEAD_TIME_BINS = [
    (0, 3, '0-3天(临期)'),
    (4, 7, '4-7天(中期)'),
    (8, 14, '8-14天(远期)'),
    (15, 999, '15天+(超远期)'),
]

FEATURE_CATEGORIES = {
    '提前期': ['days_prior', 'days_prior_sq'],
    '时间特征': ['dep_dow', 'dep_time_hour', 'dep_period_enc', 'is_weekend'],
    '节假日/展会': [
        'is_pre_holiday_peak', 'is_pre_holiday_buildup',
        'holiday_day_num', 'is_holiday_mid', 'is_holiday_last_2d',
        'is_post_holiday_dip', 'days_to_nearest_holiday',
        'expo_max_scale', 'is_expo_day',
    ],
    '航班属性': ['airline_enc', 'dep_airport_enc', 'arr_airport_enc', 'duration_hours'],
    '高铁竞争': [
        'hsr_data_available',
        'rpa_F', 'price_diff_F', 'supply_tension_F',
        'rpa_F_x_days_prior', 'supply_tension_F_x_is_holiday',
        'supply_tension_F_x_is_weekend', 'price_diff_F_x_days_prior',
        'rpa_F_x_is_weekend', 'rpa_F_high', 'rpa_F_low',
        'supply_tension_high',
        'price_F', 'remain_F', 'price_C', 'remain_C',
        'price_S', 'remain_S', 'hsr_avg_duration_h', 'train_count',
        'hsr_F_S_spread', 'hsr_total_remain',
    ],
}


# ==================== 工具函数 ====================
def assign_holiday_phase(dep_date, holiday_ranges, window_size=3):
    if hasattr(dep_date, 'date'):
        dep_date = dep_date.date()
    for s, e in holiday_ranges:
        if s <= dep_date <= e:
            day_num = (dep_date - s).days + 1
            total = (e - s).days + 1
            if day_num == 1: return '假期首日'
            elif day_num == total: return '假期末日'
            elif day_num <= total // 3: return '假期前半'
            elif day_num >= total * 2 // 3: return '假期后半'
            else: return '假期中间'
        if s - timedelta(days=window_size) <= dep_date < s:
            days_before = (s - dep_date).days
            if days_before == 1: return '节前1天'
            elif days_before <= 3: return '节前2-3天'
            else: return '节前1周内'
        if e < dep_date <= e + timedelta(days=window_size):
            days_after = (dep_date - e).days
            if days_after == 1: return '节后1天'
            else: return '节后2-3天'
    return '非节假日'


def build_scenario_labels(df, holiday_ranges):
    df = df.copy()
    df['holiday_phase'] = df['dep_date'].apply(lambda d: assign_holiday_phase(d, holiday_ranges))
    df['day_type_combo'] = np.where(df['is_weekend'] == 1, '周末',
                                    np.where(df['is_holiday'] == 1, '节假日', '工作日'))
    df['scenario'] = df['day_type_combo'] + '_' + df['holiday_phase']
    scenario_map = {}
    for s in df['scenario'].unique():
        if '节前1天' in s: scenario_map[s] = '节前高峰'
        elif '节前' in s: scenario_map[s] = '节前积蓄'
        elif '假期' in s: scenario_map[s] = '节假日'
        elif '节后' in s: scenario_map[s] = '节后回落'
        elif '周末' in s: scenario_map[s] = '周末'
        else: scenario_map[s] = '普通工作日'
    df['scenario_simple'] = df['scenario'].map(scenario_map)
    return df


def assign_lead_window(days_prior):
    if days_prior <= 3: return '0-3天(临期)'
    elif days_prior <= 7: return '4-7天(中期)'
    elif days_prior <= 14: return '8-14天(远期)'
    else: return '15天+(超远期)'


def sanitize_hsr_by_lead_time(df, hsr_cols, max_lead=14):
    df = df.copy()
    over_lead_mask = df['days_prior'] > max_lead
    n_over = over_lead_mask.sum()
    if n_over > 0:
        df.loc[over_lead_mask, 'hsr_data_available'] = 0
        cols_exist = [c for c in hsr_cols if c in df.columns]
        df.loc[over_lead_mask, cols_exist] = 0
        print(f"【清洗】{n_over} 条样本因提前期>{max_lead}天，高铁特征已清零")
    return df


def safe_mape(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = y_true != 0
    if mask.sum() == 0:
        return np.nan
    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100


def safe_adj_r2(r2, n, n_features):
    denom = n - n_features - 1
    if denom <= 0:
        return np.nan
    return 1 - (1 - r2) * (n - 1) / denom


def compute_metrics(y_true, y_pred, n_features):
    n = len(y_true)
    if n == 0:
        return {'RMSE': np.nan, 'MAE': np.nan, 'MAPE': np.nan, 'R²': np.nan,
                'Adj.R²': np.nan, 'Expl.Var': np.nan, 'ME': np.nan,
                'MaxErr': np.nan, 'MedAE': np.nan, '样本量': 0}
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mae = mean_absolute_error(y_true, y_pred)
    mape = safe_mape(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)
    adj_r2 = safe_adj_r2(r2, n, n_features)
    ev = explained_variance_score(y_true, y_pred)
    me = np.mean(y_true - y_pred)
    max_err = max_error(y_true, y_pred)
    med_ae = median_absolute_error(y_true, y_pred)
    return {
        'RMSE': round(rmse, 2), 'MAE': round(mae, 2), 'MAPE': round(mape, 2),
        'R²': round(r2, 4), 'Adj.R²': round(adj_r2, 4), 'Expl.Var': round(ev, 4),
        'ME': round(me, 2), 'MaxErr': round(max_err, 2), 'MedAE': round(med_ae, 2),
        '样本量': n,
    }


def evaluate_by_layer(y_true, y_pred, layer_labels, n_features):
    rows = []
    for layer in sorted(layer_labels.unique()):
        mask = (layer_labels == layer).values
        if mask.sum() == 0:
            continue
        res = compute_metrics(y_true[mask], y_pred[mask], n_features)
        res['分层'] = layer
        rows.append(res)
    return pd.DataFrame(rows)


def evaluate_by_scenario(y_true, y_pred, scenario_labels, n_features):
    rows = []
    for sc in sorted(scenario_labels.unique()):
        mask = (scenario_labels == sc).values
        if mask.sum() == 0:
            continue
        res = compute_metrics(y_true[mask], y_pred[mask], n_features)
        res['场景'] = sc
        rows.append(res)
    return pd.DataFrame(rows)


def shap_category_contribution(shap_values, feature_names):
    cat_contrib = {}
    total_abs = np.abs(shap_values).sum(axis=1)
    for cat, feats in FEATURE_CATEGORIES.items():
        existing = [f for f in feats if f in feature_names]
        if not existing:
            cat_contrib[cat] = 0.0
            continue
        idx = [list(feature_names).index(f) for f in existing]
        cat_abs = np.abs(shap_values[:, idx]).sum(axis=1)
        cat_contrib[cat] = round(np.mean(cat_abs / total_abs) * 100, 2)
    return cat_contrib


def shap_top_features(shap_values, feature_names, top_n=20):
    mean_abs = np.abs(shap_values).mean(axis=0)
    indices = np.argsort(mean_abs)[::-1][:top_n]
    rows = []
    for rank, idx in enumerate(indices, 1):
        rows.append({
            '排名': rank,
            '特征': feature_names[idx],
            '平均|SHAP|': round(mean_abs[idx], 2),
        })
    return pd.DataFrame(rows)


# ==================== 数据加载与预处理 ====================
print("=" * 70)
print("XGBoost 定价模型 — 分层评估 + 场景分析 + SHAP 可解释性")
print("=" * 70)

print("\n加载数据...")
features = pd.read_parquet('backend/data/feature_matrix_final_v5.parquet')
target = pd.read_parquet('backend/data/target_final_v5.parquet')

features = features.reset_index(drop=True)
target = target.reset_index(drop=True)

df = features.copy()
df['price'] = target['price']
df['query_date'] = pd.to_datetime(df['query_date']).dt.date
df['dep_date'] = pd.to_datetime(df['dep_date']).dt.date

holiday_dates_series = df['dep_date'][df['is_holiday'] == 1]
holiday_ranges = []
if not holiday_dates_series.empty:
    unique_dates = sorted(holiday_dates_series.unique())
    start = unique_dates[0]; prev = start
    for d in unique_dates[1:]:
        if (d - prev).days == 1:
            prev = d
        else:
            holiday_ranges.append((start, prev))
            start = d
            prev = d
    holiday_ranges.append((start, prev))
    min_h, max_h = df['dep_date'].min(), df['dep_date'].max()
    holiday_ranges = [(s, e) for s, e in holiday_ranges if s <= max_h and e >= min_h]

df = build_scenario_labels(df, holiday_ranges)

model_features = [
    'days_prior', 'days_prior_sq',
    'dep_dow', 'dep_time_hour', 'dep_period_enc',
    'is_weekend',
    'is_pre_holiday_peak', 'is_pre_holiday_buildup',
    'holiday_day_num', 'is_holiday_mid', 'is_holiday_last_2d',
    'is_post_holiday_dip', 'days_to_nearest_holiday',
    'expo_max_scale', 'is_expo_day',
    'airline_enc', 'dep_airport_enc', 'arr_airport_enc',
    'duration_hours',
    'hsr_data_available',
    'rpa_F', 'price_diff_F', 'supply_tension_F',
    'rpa_F_x_days_prior', 'supply_tension_F_x_is_holiday',
    'supply_tension_F_x_is_weekend', 'price_diff_F_x_days_prior',
    'rpa_F_x_is_weekend', 'rpa_F_high', 'rpa_F_low',
    'supply_tension_high',
    'price_F', 'remain_F', 'price_C', 'remain_C',
    'price_S', 'remain_S', 'hsr_avg_duration_h', 'train_count',
    'hsr_F_S_spread', 'hsr_total_remain',
]
model_features = [c for c in model_features if c in df.columns]
n_features = len(model_features)
print(f"使用特征数: {n_features}")

hsr_feature_cols = [
    'rpa_F', 'price_diff_F', 'supply_tension_F',
    'rpa_F_x_days_prior', 'supply_tension_F_x_is_holiday',
    'supply_tension_F_x_is_weekend', 'price_diff_F_x_days_prior',
    'rpa_F_x_is_weekend', 'rpa_F_high', 'rpa_F_low', 'supply_tension_high',
    'price_F', 'remain_F', 'price_C', 'remain_C',
    'price_S', 'remain_S', 'hsr_avg_duration_h', 'train_count',
    'hsr_F_S_spread', 'hsr_total_remain'
]
df = sanitize_hsr_by_lead_time(df, hsr_feature_cols, max_lead=14)

df['lead_window'] = df['days_prior'].apply(assign_lead_window)

X = df[model_features].copy()
y = df['price']

# ==================== 7:1.5:1.5 时间序划分 ====================
df = df.sort_values('query_date').reset_index(drop=True)
X = X.loc[df.index]
y = y.loc[df.index]

query_dates = sorted(df['query_date'].unique())
n_dates = len(query_dates)
train_end = query_dates[int(n_dates * 0.7)]
val_end = query_dates[int(n_dates * 0.85)]

train_mask = df['query_date'] <= train_end
val_mask = (df['query_date'] > train_end) & (df['query_date'] <= val_end)
test_mask = df['query_date'] > val_end

X_train, y_train = X[train_mask], y[train_mask]
X_val, y_val = X[val_mask], y[val_mask]
X_test, y_test = X[test_mask], y[test_mask]

imputer = SimpleImputer(strategy='median')
X_train = pd.DataFrame(imputer.fit_transform(X_train), columns=model_features, index=X_train.index)
X_val = pd.DataFrame(imputer.transform(X_val), columns=model_features, index=X_val.index)
X_test = pd.DataFrame(imputer.transform(X_test), columns=model_features, index=X_test.index)

print(f"\n时间划分（7:1.5:1.5 按 query_date）：")
print(f"  训练集：~ 至 {train_end}，{len(X_train)} 条")
print(f"  验证集：{query_dates[int(n_dates * 0.7) + 1]} ~ {val_end}，{len(X_val)} 条（早停专用）")
print(f"  测试集：{query_dates[int(n_dates * 0.85) + 1]} ~ {query_dates[-1]}，{len(X_test)} 条（最终评估）")

lead_test = df.loc[test_mask, 'lead_window']
scenario_test = df.loc[test_mask, 'scenario_simple']
days_prior_test = df.loc[test_mask, 'days_prior']

print(f"\n测试集分层分布：")
for lo, hi, label in LEAD_TIME_BINS:
    n_layer = ((days_prior_test >= lo) & (days_prior_test <= hi)).sum()
    print(f"  {label}: {n_layer} 条")

# ==================== XGBoost 模型训练 ====================
print("\n训练 XGBoost ...")
model = xgb.XGBRegressor(
    n_estimators=3000,
    early_stopping_rounds=50,
    eval_metric='rmse',
    objective='reg:squarederror',
    learning_rate=0.03,
    max_depth=12,
    subsample=0.7,
    colsample_bytree=0.7,
    reg_alpha=0.0,
    reg_lambda=1.0,
    min_child_weight=1,
    random_state=42,
    n_jobs=-1,
    verbosity=0,
)
model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
print(f"最佳迭代轮数: {model.best_iteration}（基于验证集早停）")

y_pred = model.predict(X_test)

# ==================== 整体评估 ====================
overall = compute_metrics(y_test.values, y_pred, n_features)
print("\n" + "=" * 70)
print("整体性能")
print("=" * 70)
for k, v in overall.items():
    print(f"  {k}: {v}")
pd.DataFrame([overall]).to_csv(os.path.join(OUTPUT_DIR, 'eval_overall.csv'), index=False, encoding='utf-8-sig')

# ==================== 分层评估（按提前期窗口） ====================
print("\n" + "=" * 70)
print("分层评估（按提前期窗口）")
print("=" * 70)
res_lead = evaluate_by_layer(y_test.values, y_pred, lead_test, n_features)
print(res_lead.to_string(index=False))
res_lead.to_csv(os.path.join(OUTPUT_DIR, 'eval_by_lead_window.csv'), index=False, encoding='utf-8-sig')

# ==================== 分场景评估 ====================
print("\n" + "=" * 70)
print("分场景评估")
print("=" * 70)
res_scenario = evaluate_by_scenario(y_test.values, y_pred, scenario_test, n_features)
print(res_scenario.to_string(index=False))
res_scenario.to_csv(os.path.join(OUTPUT_DIR, 'eval_by_scenario.csv'), index=False, encoding='utf-8-sig')

# ==================== 交叉分层：场景 × 提前期 ====================
print("\n" + "=" * 70)
print("交叉分层评估（场景 × 提前期窗口）")
print("=" * 70)
cross_rows = []
for sc in sorted(scenario_test.unique()):
    for lo, hi, label in LEAD_TIME_BINS:
        mask = ((scenario_test == sc) & (days_prior_test >= lo) & (days_prior_test <= hi)).values
        if mask.sum() < 10:
            continue
        res = compute_metrics(y_test.values[mask], y_pred[mask], n_features)
        res['场景'] = sc
        res['提前期'] = label
        cross_rows.append(res)
res_cross = pd.DataFrame(cross_rows)
if len(res_cross) > 0:
    print(res_cross.to_string(index=False))
    res_cross.to_csv(os.path.join(OUTPUT_DIR, 'eval_cross_scenario_lead.csv'), index=False, encoding='utf-8-sig')

# ==================== SHAP 分析 ====================
print("\n" + "=" * 70)
print("SHAP 可解释性分析")
print("=" * 70)

np.random.seed(42)
sample_size = min(5000, len(X_test))
sample_idx = np.random.choice(len(X_test), sample_size, replace=False)
X_sample = X_test.iloc[sample_idx]

print(f"  SHAP 采样: {sample_size} 条...")
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_sample)
feature_names = X_sample.columns.tolist()

# 1. 全局 Top-20 特征重要性
print("\n--- 全局 Top-20 特征重要性 ---")
top20 = shap_top_features(shap_values, feature_names, top_n=20)
print(top20.to_string(index=False))
top20.to_csv(os.path.join(OUTPUT_DIR, 'shap_top20_features.csv'), index=False, encoding='utf-8-sig')

# 1b. Top-20 特征 SHAP 散点数据（用于前端蜂群图）
mean_abs_shap = np.abs(shap_values).mean(axis=0)
top_indices = np.argsort(mean_abs_shap)[::-1][:20]
shap_scatter_rows = []
n_scatter = min(200, shap_values.shape[0])
scatter_sel = np.random.choice(shap_values.shape[0], n_scatter, replace=False)
for rank, idx in enumerate(top_indices):
    feat_name = feature_names[idx]
    for j in scatter_sel:
        shap_scatter_rows.append({
            'feature': feat_name,
            'rank': rank + 1,
            'value': round(float(X_sample.iloc[j, idx]), 6),
            'shap': round(float(shap_values[j, idx]), 6),
        })
pd.DataFrame(shap_scatter_rows).to_csv(
    os.path.join(OUTPUT_DIR, 'shap_scatter_data.csv'), index=False, encoding='utf-8-sig'
)
print(f"  SHAP 散点数据已保存 ({len(top_indices)} 特征 × {n_scatter} 样本)")

# 2. 特征分类贡献占比
print("\n--- 特征分类贡献占比 ---")
cat_contrib = shap_category_contribution(shap_values, feature_names)
for cat, pct in cat_contrib.items():
    print(f"  {cat}: {pct}%")
pd.DataFrame([cat_contrib]).to_csv(os.path.join(OUTPUT_DIR, 'shap_category_contribution.csv'), index=False, encoding='utf-8-sig')

# 3. 分提前期 SHAP 分类贡献
print("\n--- 分提前期 SHAP 分类贡献 ---")
lead_sample = df.loc[test_mask, 'lead_window'].iloc[sample_idx]
lead_shap_rows = []
for lo, hi, label in LEAD_TIME_BINS:
    mask = (lead_sample == label).values
    if mask.sum() < 20:
        continue
    sv = shap_values[mask]
    cat_c = shap_category_contribution(sv, feature_names)
    cat_c['提前期'] = label
    cat_c['样本数'] = mask.sum()
    lead_shap_rows.append(cat_c)
res_lead_shap = pd.DataFrame(lead_shap_rows)
print(res_lead_shap.to_string(index=False))
res_lead_shap.to_csv(os.path.join(OUTPUT_DIR, 'shap_contribution_by_lead.csv'), index=False, encoding='utf-8-sig')

# 4. 分场景 SHAP 分类贡献
print("\n--- 分场景 SHAP 分类贡献 ---")
scenario_sample = df.loc[test_mask, 'scenario_simple'].iloc[sample_idx]
scenario_shap_rows = []
for sc in sorted(scenario_sample.unique()):
    mask = (scenario_sample == sc).values
    if mask.sum() < 20:
        continue
    sv = shap_values[mask]
    cat_c = shap_category_contribution(sv, feature_names)
    cat_c['场景'] = sc
    cat_c['样本数'] = mask.sum()
    scenario_shap_rows.append(cat_c)
res_scenario_shap = pd.DataFrame(scenario_shap_rows)
print(res_scenario_shap.to_string(index=False))
res_scenario_shap.to_csv(os.path.join(OUTPUT_DIR, 'shap_contribution_by_scenario.csv'), index=False, encoding='utf-8-sig')

# 5. 高铁竞争特征深度分析
print("\n--- 高铁竞争特征深度分析 ---")
hsr_core = ['rpa_F', 'supply_tension_F', 'price_diff_F']
hsr_core = [f for f in hsr_core if f in feature_names]
hsr_all = [f for f in FEATURE_CATEGORIES['高铁竞争'] if f in feature_names]

total_abs = np.abs(shap_values).sum(axis=1)

hsr_all_idx = [feature_names.index(f) for f in hsr_all]
hsr_all_contrib = np.abs(shap_values[:, hsr_all_idx]).sum(axis=1)
pct_hsr_all = np.mean(hsr_all_contrib / total_abs) * 100

hsr_avail_mask = (df.loc[test_mask, 'hsr_data_available'].iloc[sample_idx] == 1).values
if hsr_avail_mask.sum() > 0:
    sv_avail = shap_values[hsr_avail_mask]
    total_avail = np.abs(sv_avail).sum(axis=1)
    hsr_avail_contrib = np.abs(sv_avail[:, hsr_all_idx]).sum(axis=1)
    pct_hsr_avail = np.mean(hsr_avail_contrib / total_avail) * 100
    print(f"  高铁有效样本中（n={hsr_avail_mask.sum()}）：高铁特征贡献 {pct_hsr_avail:.1f}%")
    if hsr_core:
        hsr_core_idx = [feature_names.index(f) for f in hsr_core]
        core_contrib = np.abs(sv_avail[:, hsr_core_idx]).sum(axis=1)
        pct_core = np.mean(core_contrib / total_avail) * 100
        print(f"  核心竞争特征（{hsr_core}）贡献: {pct_core:.1f}%")
else:
    pct_hsr_avail = 0
    pct_core = 0

print(f"  全部样本：高铁特征贡献 {pct_hsr_all:.1f}%")

# 6. 分提前期高铁贡献
print("\n--- 分提前期高铁贡献 ---")
hsr_lead_rows = []
for lo, hi, label in LEAD_TIME_BINS:
    mask_lead = (lead_sample == label).values
    mask_combined = mask_lead & hsr_avail_mask
    n_combined = mask_combined.sum()
    if n_combined < 20:
        print(f"  {label}: 高铁有效样本不足 ({n_combined})")
        hsr_lead_rows.append({'提前期': label, '样本数': n_combined, '高铁贡献%': np.nan, '核心竞争贡献%': np.nan})
        continue
    sv_sub = shap_values[mask_combined]
    total_sub = np.abs(sv_sub).sum(axis=1)
    hsr_sub = np.abs(sv_sub[:, hsr_all_idx]).sum(axis=1)
    pct_sub = np.mean(hsr_sub / total_sub) * 100
    pct_core_sub = 0
    if hsr_core:
        hsr_core_idx_sub = [feature_names.index(f) for f in hsr_core]
        core_sub = np.abs(sv_sub[:, hsr_core_idx_sub]).sum(axis=1)
        pct_core_sub = np.mean(core_sub / total_sub) * 100
    print(f"  {label}: 高铁贡献 {pct_sub:.1f}% | 核心竞争 {pct_core_sub:.1f}% | n={n_combined}")
    hsr_lead_rows.append({'提前期': label, '样本数': n_combined, '高铁贡献%': round(pct_sub, 2), '核心竞争贡献%': round(pct_core_sub, 2)})
pd.DataFrame(hsr_lead_rows).to_csv(os.path.join(OUTPUT_DIR, 'shap_hsr_by_lead.csv'), index=False, encoding='utf-8-sig')

# 7. 分场景高铁贡献
print("\n--- 分场景高铁贡献 ---")
hsr_scenario_rows = []
for sc in sorted(scenario_sample.unique()):
    mask_sc = (scenario_sample == sc).values
    mask_combined = mask_sc & hsr_avail_mask
    n_combined = mask_combined.sum()
    if n_combined < 20:
        hsr_scenario_rows.append({'场景': sc, '样本数': n_combined, '高铁贡献%': np.nan, '核心竞争贡献%': np.nan})
        continue
    sv_sub = shap_values[mask_combined]
    total_sub = np.abs(sv_sub).sum(axis=1)
    hsr_sub = np.abs(sv_sub[:, hsr_all_idx]).sum(axis=1)
    pct_sub = np.mean(hsr_sub / total_sub) * 100
    pct_core_sub = 0
    if hsr_core:
        hsr_core_idx_sub = [feature_names.index(f) for f in hsr_core]
        core_sub = np.abs(sv_sub[:, hsr_core_idx_sub]).sum(axis=1)
        pct_core_sub = np.mean(core_sub / total_sub) * 100
    print(f"  {sc}: 高铁贡献 {pct_sub:.1f}% | 核心竞争 {pct_core_sub:.1f}% | n={n_combined}")
    hsr_scenario_rows.append({'场景': sc, '样本数': n_combined, '高铁贡献%': round(pct_sub, 2), '核心竞争贡献%': round(pct_core_sub, 2)})
pd.DataFrame(hsr_scenario_rows).to_csv(os.path.join(OUTPUT_DIR, 'shap_hsr_by_scenario.csv'), index=False, encoding='utf-8-sig')

# 8. SHAP 图表
print("\n生成 SHAP 图表...")

fig, ax = plt.subplots(figsize=(10, 8))
shap.summary_plot(shap_values, X_sample, max_display=20, show=False)
plt.title('XGBoost 全局特征重要性（SHAP）')
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'shap_summary.png'), dpi=150, bbox_inches='tight')
plt.close()

if 'rpa_F' in feature_names:
    fig, ax = plt.subplots(figsize=(8, 5))
    rpa_shap = shap_values[:, feature_names.index('rpa_F')]
    ax.scatter(X_sample['rpa_F'], rpa_shap, alpha=0.3, s=10, c='steelblue')
    ax.axhline(y=0, color='red', linestyle='--', linewidth=0.8)
    ax.set_xlabel('高铁-航空价格比 (RPA)', fontsize=12)
    ax.set_ylabel('RPA 的 SHAP 值', fontsize=12)
    ax.set_title('RPA 对航空票价的边际影响（SHAP）', fontsize=13)
    try:
        from statsmodels.nonparametric.smoothers_lowess import lowess
        z = lowess(rpa_shap, X_sample['rpa_F'], frac=0.3)
        ax.plot(z[:, 0], z[:, 1], color='darkred', linewidth=2, label='LOWESS趋势')
        ax.legend()
    except Exception:
        pass
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'shap_rpa_dependence.png'), dpi=150, bbox_inches='tight')
    plt.close()

if 'supply_tension_F' in feature_names:
    fig, ax = plt.subplots(figsize=(8, 5))
    st_shap = shap_values[:, feature_names.index('supply_tension_F')]
    ax.scatter(X_sample['supply_tension_F'], st_shap, alpha=0.3, s=10, c='steelblue')
    ax.axhline(y=0, color='red', linestyle='--', linewidth=0.8)
    ax.set_xlabel('高铁供给紧张度', fontsize=12)
    ax.set_ylabel('供给紧张度 SHAP 值', fontsize=12)
    ax.set_title('高铁供给紧张度对航空票价的边际影响', fontsize=13)
    try:
        from statsmodels.nonparametric.smoothers_lowess import lowess
        z = lowess(st_shap, X_sample['supply_tension_F'], frac=0.3)
        ax.plot(z[:, 0], z[:, 1], color='darkred', linewidth=2, label='LOWESS趋势')
        ax.legend()
    except Exception:
        pass
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'shap_supply_tension_dependence.png'), dpi=150, bbox_inches='tight')
    plt.close()

cat_names = list(cat_contrib.keys())
cat_pcts = list(cat_contrib.values())
fig, ax = plt.subplots(figsize=(8, 5))
colors = ['#4e79a7', '#f28e2b', '#e15759', '#76b7b2', '#59a14f']
bars = ax.barh(cat_names, cat_pcts, color=colors[:len(cat_names)])
ax.set_xlabel('平均贡献占比 (%)', fontsize=12)
ax.set_title('SHAP 特征分类贡献占比', fontsize=13)
for bar, pct in zip(bars, cat_pcts):
    ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
            f'{pct:.1f}%', va='center', fontsize=10)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'shap_category_bar.png'), dpi=150, bbox_inches='tight')
plt.close()

# ==================== 参数敏感性分析 ====================
print("\n" + "=" * 70)
print("XGBoost 参数敏感性分析")
print("=" * 70)

base_params = {
    'objective': 'reg:squarederror',
    'learning_rate': 0.03,
    'max_depth': 12,
    'subsample': 0.7,
    'colsample_bytree': 0.7,
    'reg_alpha': 0.0,
    'reg_lambda': 1.0,
    'min_child_weight': 1,
}

param_list = {
    'learning_rate': [0.01, 0.02, 0.03, 0.05, 0.1],
    'max_depth': [4, 6, 8, 10, 12],
    'subsample': [0.6, 0.7, 0.8, 0.9, 1.0],
    'colsample_bytree': [0.5, 0.6, 0.7, 0.8, 1.0],
    'reg_alpha': [0, 0.05, 0.1, 0.5, 1.0],
    'reg_lambda': [0.1, 0.3, 0.5, 1.0, 2.0],
    'min_child_weight': [1, 3, 5, 10],
}

all_sensitivity = {}

for param_name, values in param_list.items():
    print(f"\n分析 {param_name}...")
    rows = []
    for val in values:
        params = base_params.copy()
        params[param_name] = val
        m = xgb.XGBRegressor(
            n_estimators=3000,
            early_stopping_rounds=50,
            eval_metric='rmse',
            **params,
            random_state=42,
            n_jobs=-1,
            verbosity=0,
        )
        m.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
        yp = m.predict(X_test)
        res = compute_metrics(y_test.values, yp, n_features)
        res['参数值'] = val
        res['best_iteration'] = m.best_iteration
        rows.append(res)
    sens_df = pd.DataFrame(rows)
    cols = ['参数值'] + [c for c in sens_df.columns if c != '参数值']
    sens_df = sens_df[cols]
    sens_df.to_csv(os.path.join(OUTPUT_DIR, f'sensitivity_{param_name}.csv'), index=False, encoding='utf-8-sig')
    all_sensitivity[param_name] = sens_df

    best_mape_idx = sens_df['MAPE'].idxmin()
    print(f"  MAPE最优: {param_name}={sens_df.loc[best_mape_idx, '参数值']} "
          f"(MAPE={sens_df.loc[best_mape_idx, 'MAPE']}%, RMSE={sens_df.loc[best_mape_idx, 'RMSE']})")

summary_rows = []
for param_name, sdf in all_sensitivity.items():
    best_idx = sdf['MAPE'].idxmin()
    summary_rows.append({
        '参数名': param_name,
        '最优值': sdf.loc[best_idx, '参数值'],
        'RMSE': sdf.loc[best_idx, 'RMSE'],
        'MAPE': sdf.loc[best_idx, 'MAPE'],
        'R²': sdf.loc[best_idx, 'R²'],
        'best_iteration': sdf.loc[best_idx, 'best_iteration'],
    })
summary_df = pd.DataFrame(summary_rows)
print("\n--- 各参数最优值汇总 ---")
print(summary_df.to_string(index=False))
summary_df.to_csv(os.path.join(OUTPUT_DIR, 'sensitivity_summary.csv'), index=False, encoding='utf-8-sig')

# ==================== 保存模型 ====================
model.get_booster().save_model('backend/data/xgb_air_hsr_model_v5.json')
print(f"\n模型已保存至: backend/data/xgb_air_hsr_model_v5.json")

# ==================== 汇总输出 ====================
print("\n" + "=" * 70)
print("所有结果已保存至 output/ 文件夹：")
print("=" * 70)
output_files = [
    'eval_overall.csv',
    'eval_by_lead_window.csv',
    'eval_by_scenario.csv',
    'eval_cross_scenario_lead.csv',
    'shap_top20_features.csv',
    'shap_scatter_data.csv',
    'shap_category_contribution.csv',
    'shap_contribution_by_lead.csv',
    'shap_contribution_by_scenario.csv',
    'shap_hsr_by_lead.csv',
    'shap_hsr_by_scenario.csv',
    'shap_summary.png',
    'shap_rpa_dependence.png',
    'shap_supply_tension_dependence.png',
    'shap_category_bar.png',
    'sensitivity_summary.csv',
]
for f in output_files:
    path = os.path.join(OUTPUT_DIR, f)
    if os.path.exists(path):
        print(f"  ✓ {f}")
    else:
        print(f"  ✗ {f} (未生成)")
for param_name in param_list:
    f = f'sensitivity_{param_name}.csv'
    path = os.path.join(OUTPUT_DIR, f)
    if os.path.exists(path):
        print(f"  ✓ {f}")

print("\n" + "=" * 70)
print("完成！")
print("=" * 70)
# %%
