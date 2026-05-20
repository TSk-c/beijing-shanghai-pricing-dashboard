"""
附录B：多模型对比实验
8 算法（Ridge/Lasso/ElasticNet/RF/XGBoost/LightGBM/GBDT/LSTM）
7:1.5:1.5 时间序划分 | 分层评估 | MAPE 主指标
依赖：需先运行 feature_engineering.py 生成 .parquet 文件
"""

import numpy as np
import pandas as pd
import os
import time
import warnings
warnings.filterwarnings('ignore')

from sklearn.linear_model import Ridge, Lasso, ElasticNet
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler
from datetime import timedelta

import xgboost as xgb
import lightgbm as lgb

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

RANDOM_STATE = 42
SEQ_LEN = 7
OUTPUT_DIR = 'output_model_vs'
np.random.seed(RANDOM_STATE)
torch.manual_seed(RANDOM_STATE)

os.makedirs(OUTPUT_DIR, exist_ok=True)

CSV_OVERALL = os.path.join(OUTPUT_DIR, 'model_comparison_v2_overall.csv')
CSV_LAYERED = os.path.join(OUTPUT_DIR, 'model_comparison_v2_layered.csv')

LEAD_TIME_BINS = [
    (0, 3, '0-3天(临期)'),
    (4, 7, '4-7天(中期)'),
    (8, 14, '8-14天(远期)'),
    (15, 999, '15天+(超远期)'),
]


def sanitize_hsr_by_lead_time(df, hsr_cols, max_lead=14):
    df = df.copy()
    over_lead_mask = df['days_prior'] > max_lead
    n_over = over_lead_mask.sum()
    if n_over > 0:
        df.loc[over_lead_mask, 'hsr_data_available'] = 0
        cols_exist = [c for c in hsr_cols if c in df.columns]
        df.loc[over_lead_mask, cols_exist] = 0
        print(f"  【清洗】{n_over} 条样本因提前期>{max_lead}天，高铁特征已清零")
    return df


def build_scenario_labels(df, holiday_ranges):
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


def safe_mape(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = y_true != 0
    if mask.sum() == 0:
        return np.nan
    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100


def evaluate_model(y_true, y_pred, model_name, n_features):
    n = len(y_true)
    if n == 0:
        return {'模型': model_name, 'RMSE': np.nan, 'MAE': np.nan, 'MAPE': np.nan, 'R²': np.nan, 'Adj.R²': np.nan, '样本数': 0}
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mae = mean_absolute_error(y_true, y_pred)
    mape = safe_mape(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)
    denom = n - n_features - 1
    adj_r2 = 1 - (1 - r2) * (n - 1) / denom if denom > 0 else np.nan
    return {
        '模型': model_name,
        'RMSE': round(rmse, 2),
        'MAE': round(mae, 2),
        'MAPE': round(mape, 2),
        'R²': round(r2, 4),
        'Adj.R²': round(adj_r2, 4),
        '样本数': n,
    }


def save_csv(results, path):
    df = pd.DataFrame(results)
    df = df.sort_values('MAPE').reset_index(drop=True)
    df.to_csv(path, index=False, encoding='utf-8-sig')


def load_and_split():
    print("加载数据...")
    features = pd.read_parquet('backend/data/feature_matrix_final_v5.parquet')
    target = pd.read_parquet('backend/data/target_final_v5.parquet')
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
            if (d - prev).days == 1: prev = d
            else: holiday_ranges.append((start, prev)); start = d; prev = d
        holiday_ranges.append((start, prev))

    df = build_scenario_labels(df, holiday_ranges)

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

    model_features = [
        'days_prior', 'days_prior_sq', 'dep_dow', 'dep_time_hour', 'dep_period_enc',
        'is_weekend', 'is_pre_holiday_peak', 'is_pre_holiday_buildup',
        'holiday_day_num', 'is_holiday_mid', 'is_holiday_last_2d',
        'is_post_holiday_dip', 'days_to_nearest_holiday',
        'expo_max_scale', 'is_expo_day', 'hsr_data_available',
        'price_C', 'price_F', 'price_S', 'remain_C', 'remain_F', 'remain_S',
        'hsr_avg_duration_h', 'train_count',
        'rpa_F', 'price_diff_F', 'supply_tension_F',
        'rpa_F_x_days_prior', 'supply_tension_F_x_is_holiday',
        'supply_tension_F_x_is_weekend', 'price_diff_F_x_days_prior',
        'rpa_F_x_is_weekend', 'rpa_F_high', 'rpa_F_low',
        'supply_tension_high', 'hsr_F_S_spread', 'hsr_total_remain',
        'airline_enc', 'dep_airport_enc', 'arr_airport_enc', 'duration_hours'
    ]
    model_features = [c for c in model_features if c in df.columns]
    n_features = len(model_features)
    print(f"  使用特征数: {n_features}")

    df = df.sort_values('query_date').reset_index(drop=True)
    query_dates = sorted(df['query_date'].unique())
    n_dates = len(query_dates)
    print(f"  query_date 总天数: {n_dates}")
    print(f"  日期范围: {query_dates[0]} ~ {query_dates[-1]}")
    print(f"  总样本量: {len(df)}")

    train_end = query_dates[int(n_dates * 0.7)]
    val_end = query_dates[int(n_dates * 0.85)]

    train_mask = df['query_date'] <= train_end
    val_mask = (df['query_date'] > train_end) & (df['query_date'] <= val_end)
    test_mask = df['query_date'] > val_end

    X = df[model_features].copy()
    y = df['price'].copy()

    X_train = X.loc[train_mask].copy()
    y_train = y.loc[train_mask].copy()
    X_val = X.loc[val_mask].copy()
    y_val = y.loc[val_mask].copy()
    X_test = X.loc[test_mask].copy()
    y_test = y.loc[test_mask].copy()

    imputer = SimpleImputer(strategy='median')
    X_train_imp = pd.DataFrame(imputer.fit_transform(X_train), columns=model_features, index=X_train.index)
    X_val_imp = pd.DataFrame(imputer.transform(X_val), columns=model_features, index=X_val.index)
    X_test_imp = pd.DataFrame(imputer.transform(X_test), columns=model_features, index=X_test.index)

    scaler = StandardScaler()
    X_train_sc = pd.DataFrame(scaler.fit_transform(X_train_imp), columns=model_features, index=X_train.index)
    X_val_sc = pd.DataFrame(scaler.transform(X_val_imp), columns=model_features, index=X_val.index)
    X_test_sc = pd.DataFrame(scaler.transform(X_test_imp), columns=model_features, index=X_test.index)

    print(f"  时间划分：训练{len(X_train_imp)}条 | 验证{len(X_val_imp)}条 | 测试{len(X_test_imp)}条")

    meta = {
        'df': df, 'model_features': model_features, 'n_features': n_features,
        'train_mask': train_mask, 'val_mask': val_mask, 'test_mask': test_mask,
        'imputer': imputer, 'scaler': scaler,
    }
    return (X_train_imp, y_train, X_val_imp, y_val, X_test_imp, y_test,
            X_train_sc, X_val_sc, X_test_sc, meta)


def build_3d_all(df, model_features, train_mask, val_mask, test_mask, seq_len=SEQ_LEN):
    all_sub = df.copy()
    all_sub = all_sub.sort_values(['flight_no', 'dep_date', 'days_prior']).reset_index(drop=True)

    train_idx = set(df.loc[train_mask].index)
    val_idx = set(df.loc[val_mask].index)
    test_idx = set(df.loc[test_mask].index)

    X_train_list, y_train_list = [], []
    X_val_list, y_val_list = [], []
    X_test_list, y_test_list, lead_test_list = [], [], []

    for (fn, dd), grp in all_sub.groupby(['flight_no', 'dep_date']):
        if len(grp) < seq_len:
            continue
        grp = grp.sort_values('days_prior')
        feat = grp[model_features].values.astype(np.float32)
        prices = grp['price'].values.astype(np.float32)
        leads = grp['days_prior'].values.astype(np.float32)
        indices = grp.index.values

        for i in range(len(grp) - seq_len + 1):
            last_idx = indices[i + seq_len - 1]
            x_seq = feat[i:i + seq_len]
            y_val_seq = prices[i + seq_len - 1]
            lead_val = leads[i + seq_len - 1]

            if last_idx in train_idx:
                X_train_list.append(x_seq)
                y_train_list.append(y_val_seq)
            elif last_idx in val_idx:
                X_val_list.append(x_seq)
                y_val_list.append(y_val_seq)
            elif last_idx in test_idx:
                X_test_list.append(x_seq)
                y_test_list.append(y_val_seq)
                lead_test_list.append(lead_val)

    X_tr = np.stack(X_train_list) if X_train_list else np.array([])
    y_tr = np.array(y_train_list) if y_train_list else np.array([])
    X_va = np.stack(X_val_list) if X_val_list else np.array([])
    y_va = np.array(y_val_list) if y_val_list else np.array([])
    X_te = np.stack(X_test_list) if X_test_list else np.array([])
    y_te = np.array(y_test_list) if y_test_list else np.array([])
    lead_te = np.array(lead_test_list) if lead_test_list else np.array([])

    return X_tr, y_tr, X_va, y_va, X_te, y_te, lead_te


# ============================================================
# 模型 1：Ridge
# ============================================================
def train_ridge(X_train_sc, y_train, X_test_sc, y_test, n_features):
    print("\n[1/8] Ridge 回归...")
    t0 = time.time()
    model = Ridge(alpha=1.0, random_state=RANDOM_STATE)
    model.fit(X_train_sc, y_train)
    y_pred = model.predict(X_test_sc)
    elapsed = time.time() - t0
    print(f"  Ridge 完成，耗时 {elapsed:.1f}s")
    return y_test.values, y_pred, elapsed


# ============================================================
# 模型 2：Lasso
# ============================================================
def train_lasso(X_train_sc, y_train, X_test_sc, y_test, n_features):
    print("\n[2/8] Lasso 回归...")
    t0 = time.time()
    model = Lasso(alpha=1.0, random_state=RANDOM_STATE, max_iter=5000)
    model.fit(X_train_sc, y_train)
    y_pred = model.predict(X_test_sc)
    n_zero = np.sum(np.abs(model.coef_) < 1e-6)
    elapsed = time.time() - t0
    print(f"  Lasso 完成，{n_zero}/{len(model.coef_)} 个系数为零，耗时 {elapsed:.1f}s")
    return y_test.values, y_pred, elapsed


# ============================================================
# 模型 3：ElasticNet
# ============================================================
def train_elasticnet(X_train_sc, y_train, X_test_sc, y_test, n_features):
    print("\n[3/8] ElasticNet 回归...")
    t0 = time.time()
    model = ElasticNet(alpha=1.0, l1_ratio=0.5, random_state=RANDOM_STATE, max_iter=5000)
    model.fit(X_train_sc, y_train)
    y_pred = model.predict(X_test_sc)
    elapsed = time.time() - t0
    print(f"  ElasticNet 完成，耗时 {elapsed:.1f}s")
    return y_test.values, y_pred, elapsed


# ============================================================
# 模型 4：随机森林
# ============================================================
def train_rf(X_train, y_train, X_test, y_test, n_features):
    print("\n[4/8] 随机森林...")
    t0 = time.time()
    rf = RandomForestRegressor(
        n_estimators=500, max_depth=15, min_samples_split=5,
        min_samples_leaf=2, max_features='sqrt',
        n_jobs=-1, random_state=RANDOM_STATE,
    )
    rf.fit(X_train, y_train)
    y_pred = rf.predict(X_test)
    elapsed = time.time() - t0
    print(f"  RF 完成，耗时 {elapsed:.1f}s")
    return y_test.values, y_pred, elapsed


# ============================================================
# 模型 5：XGBoost
# ============================================================
def train_xgb(X_train, y_train, X_val, y_val, X_test, y_test, n_features):
    print("\n[5/8] XGBoost（验证集早停）...")
    t0 = time.time()
    model = xgb.XGBRegressor(
        n_estimators=3000,
        early_stopping_rounds=50,
        eval_metric='rmse',
        objective='reg:squarederror',
        learning_rate=0.02,
        max_depth=8,
        subsample=0.8,
        colsample_bytree=0.7,
        reg_alpha=0.1,
        reg_lambda=0.3,
        min_child_weight=3,
        random_state=RANDOM_STATE,
        n_jobs=-1,
        verbosity=0,
    )
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
    y_pred = model.predict(X_test)
    elapsed = time.time() - t0
    print(f"  XGBoost 完成，最佳迭代={model.best_iteration}，耗时 {elapsed:.1f}s")
    return y_test.values, y_pred, elapsed


# ============================================================
# 模型 6：LightGBM
# ============================================================
def train_lgb(X_train, y_train, X_val, y_val, X_test, y_test, n_features):
    print("\n[6/8] LightGBM（验证集早停）...")
    t0 = time.time()
    model = lgb.LGBMRegressor(
        n_estimators=3000,
        learning_rate=0.02,
        max_depth=8,
        num_leaves=63,
        subsample=0.8,
        colsample_bytree=0.7,
        reg_alpha=0.1,
        reg_lambda=0.3,
        min_child_samples=20,
        random_state=RANDOM_STATE,
        n_jobs=-1,
        verbose=-1,
    )
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)],
              callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(0)])
    y_pred = model.predict(X_test)
    elapsed = time.time() - t0
    print(f"  LightGBM 完成，最佳迭代={model.best_iteration_}，耗时 {elapsed:.1f}s")
    return y_test.values, y_pred, elapsed


# ============================================================
# 模型 7：GradientBoosting
# ============================================================
def train_gbdt(X_train, y_train, X_val, y_val, X_test, y_test, n_features):
    print("\n[7/8] GradientBoosting（sklearn）...")
    t0 = time.time()
    model = GradientBoostingRegressor(
        n_estimators=500,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        min_samples_split=5,
        min_samples_leaf=2,
        max_features='sqrt',
        random_state=RANDOM_STATE,
    )
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    elapsed = time.time() - t0
    print(f"  GradientBoosting 完成，耗时 {elapsed:.1f}s")
    return y_test.values, y_pred, elapsed


# ============================================================
# 模型 8：LSTM
# ============================================================
class LSTMModel(nn.Module):
    def __init__(self, input_dim, hidden1=64, hidden2=32, dropout=0.1):
        super().__init__()
        self.lstm1 = nn.LSTM(input_dim, hidden1, batch_first=True)
        self.drop1 = nn.Dropout(dropout)
        self.lstm2 = nn.LSTM(hidden1, hidden2, batch_first=True)
        self.drop2 = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden2, 1)

    def forward(self, x):
        out, _ = self.lstm1(x)
        out = self.drop1(out)
        out, _ = self.lstm2(out)
        out = self.drop2(out[:, -1, :])
        return self.fc(out)


def train_lstm(X_train_3d, y_train_3d, X_val_3d, y_val_3d, X_test_3d, y_test_3d, input_dim):
    print("\n[8/8] LSTM（隐藏层 64→32，Dropout=0.1）...")
    t0 = time.time()
    model = LSTMModel(input_dim)
    model = _train_deep(model, X_train_3d, y_train_3d, X_val_3d, y_val_3d,
                        epochs=30, batch_size=256, lr=1e-3, patience=7)
    model.eval()
    with torch.no_grad():
        y_pred = model(torch.FloatTensor(X_test_3d)).squeeze().numpy()
    elapsed = time.time() - t0
    print(f"  LSTM 完成，耗时 {elapsed:.1f}s")
    return y_test_3d, y_pred, elapsed


def _train_deep(model, X_train_3d, y_train_3d, X_val_3d, y_val_3d,
                epochs=30, batch_size=256, lr=1e-3, patience=7):
    device = 'cpu'
    model = model.to(device)
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    train_ds = TensorDataset(torch.FloatTensor(X_train_3d), torch.FloatTensor(y_train_3d))
    val_ds = TensorDataset(torch.FloatTensor(X_val_3d), torch.FloatTensor(y_val_3d))
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)

    best_val_loss = np.inf
    best_state = None
    wait = 0

    for epoch in range(1, epochs + 1):
        model.train()
        train_losses = []
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            pred = model(xb).squeeze()
            loss = criterion(pred, yb)
            loss.backward()
            optimizer.step()
            train_losses.append(loss.item())

        model.eval()
        val_losses = []
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(device), yb.to(device)
                pred = model(xb).squeeze()
                val_losses.append(criterion(pred, yb).item())
        val_loss = np.mean(val_losses)

        if epoch % 5 == 0 or epoch == 1:
            print(f"    Epoch {epoch}/{epochs}  train_loss={np.mean(train_losses):.2f}  val_loss={val_loss:.2f}")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            wait = 0
        else:
            wait += 1
            if wait >= patience:
                print(f"    早停于 epoch {epoch}，最佳 val_loss={best_val_loss:.2f}")
                break

    if best_state is not None:
        model.load_state_dict(best_state)
    return model


# ============================================================
# 分层评估
# ============================================================
def layered_evaluate(y_true, y_pred, days_prior_test, model_name, n_features):
    results = []
    for lo, hi, label in LEAD_TIME_BINS:
        mask = (days_prior_test >= lo) & (days_prior_test <= hi)
        if mask.sum() == 0:
            results.append({'模型': model_name, '分层': label, 'RMSE': np.nan, 'MAE': np.nan,
                           'MAPE': np.nan, 'R²': np.nan, '样本数': 0})
            continue
        yt = np.asarray(y_true)[mask]
        yp = np.asarray(y_pred)[mask]
        res = evaluate_model(yt, yp, model_name, n_features)
        res['分层'] = label
        results.append(res)
    return results


# ============================================================
# 主流程
# ============================================================
def main():
    print("多模型对比实验（7:1.5:1.5 | 8 模型）")

    (X_train, y_train, X_val, y_val, X_test, y_test,
     X_train_sc, X_val_sc, X_test_sc, meta) = load_and_split()

    df = meta['df']
    model_features = meta['model_features']
    n_features = meta['n_features']
    train_mask = meta['train_mask']
    val_mask = meta['val_mask']
    test_mask = meta['test_mask']

    days_prior_test = df.loc[test_mask, 'days_prior'].values

    all_overall = []
    all_layered = []

    # --- 1. Ridge ---
    y_true, y_pred, t = train_ridge(X_train_sc, y_train, X_test_sc, y_test, n_features)
    res = evaluate_model(y_true, y_pred, 'Ridge', n_features)
    res['耗时(s)'] = round(t, 1)
    all_overall.append(res)
    all_layered.extend(layered_evaluate(y_true, y_pred, days_prior_test, 'Ridge', n_features))
    save_csv(all_overall, CSV_OVERALL)
    save_csv(all_layered, CSV_LAYERED)
    print(f"  → MAPE={res['MAPE']}%, MAE={res['MAE']}, RMSE={res['RMSE']}")

    # --- 2. Lasso ---
    y_true, y_pred, t = train_lasso(X_train_sc, y_train, X_test_sc, y_test, n_features)
    res = evaluate_model(y_true, y_pred, 'Lasso', n_features)
    res['耗时(s)'] = round(t, 1)
    all_overall.append(res)
    all_layered.extend(layered_evaluate(y_true, y_pred, days_prior_test, 'Lasso', n_features))
    save_csv(all_overall, CSV_OVERALL)
    save_csv(all_layered, CSV_LAYERED)
    print(f"  → MAPE={res['MAPE']}%, MAE={res['MAE']}, RMSE={res['RMSE']}")

    # --- 3. ElasticNet ---
    y_true, y_pred, t = train_elasticnet(X_train_sc, y_train, X_test_sc, y_test, n_features)
    res = evaluate_model(y_true, y_pred, 'ElasticNet', n_features)
    res['耗时(s)'] = round(t, 1)
    all_overall.append(res)
    all_layered.extend(layered_evaluate(y_true, y_pred, days_prior_test, 'ElasticNet', n_features))
    save_csv(all_overall, CSV_OVERALL)
    save_csv(all_layered, CSV_LAYERED)
    print(f"  → MAPE={res['MAPE']}%, MAE={res['MAE']}, RMSE={res['RMSE']}")

    # --- 4. 随机森林 ---
    y_true, y_pred, t = train_rf(X_train, y_train, X_test, y_test, n_features)
    res = evaluate_model(y_true, y_pred, '随机森林', n_features)
    res['耗时(s)'] = round(t, 1)
    all_overall.append(res)
    all_layered.extend(layered_evaluate(y_true, y_pred, days_prior_test, '随机森林', n_features))
    save_csv(all_overall, CSV_OVERALL)
    save_csv(all_layered, CSV_LAYERED)
    print(f"  → MAPE={res['MAPE']}%, MAE={res['MAE']}, RMSE={res['RMSE']}")

    # --- 5. XGBoost ---
    y_true, y_pred, t = train_xgb(X_train, y_train, X_val, y_val, X_test, y_test, n_features)
    res = evaluate_model(y_true, y_pred, 'XGBoost', n_features)
    res['耗时(s)'] = round(t, 1)
    all_overall.append(res)
    all_layered.extend(layered_evaluate(y_true, y_pred, days_prior_test, 'XGBoost', n_features))
    save_csv(all_overall, CSV_OVERALL)
    save_csv(all_layered, CSV_LAYERED)
    print(f"  → MAPE={res['MAPE']}%, MAE={res['MAE']}, RMSE={res['RMSE']}")

    # --- 6. LightGBM ---
    y_true, y_pred, t = train_lgb(X_train, y_train, X_val, y_val, X_test, y_test, n_features)
    res = evaluate_model(y_true, y_pred, 'LightGBM', n_features)
    res['耗时(s)'] = round(t, 1)
    all_overall.append(res)
    all_layered.extend(layered_evaluate(y_true, y_pred, days_prior_test, 'LightGBM', n_features))
    save_csv(all_overall, CSV_OVERALL)
    save_csv(all_layered, CSV_LAYERED)
    print(f"  → MAPE={res['MAPE']}%, MAE={res['MAE']}, RMSE={res['RMSE']}")

    # --- 7. GradientBoosting ---
    y_true, y_pred, t = train_gbdt(X_train, y_train, X_val, y_val, X_test, y_test, n_features)
    res = evaluate_model(y_true, y_pred, 'GradientBoosting', n_features)
    res['耗时(s)'] = round(t, 1)
    all_overall.append(res)
    all_layered.extend(layered_evaluate(y_true, y_pred, days_prior_test, 'GradientBoosting', n_features))
    save_csv(all_overall, CSV_OVERALL)
    save_csv(all_layered, CSV_LAYERED)
    print(f"  → MAPE={res['MAPE']}%, MAE={res['MAE']}, RMSE={res['RMSE']}")

    # --- 8. LSTM ---
    print("\n构建三维滑动窗口数据（按 flight_no+dep_date 分组，序列长度=7）...")
    X_train_3d, y_train_3d, X_val_3d, y_val_3d, X_test_3d, y_test_3d, lead_test_3d = \
        build_3d_all(df, model_features, train_mask, val_mask, test_mask)
    input_dim = X_train_3d.shape[2] if len(X_train_3d) > 0 else n_features
    print(f"  训练 3D: {X_train_3d.shape}, 验证 3D: {X_val_3d.shape}, 测试 3D: {X_test_3d.shape}")

    if len(X_train_3d) > 0 and len(X_val_3d) > 0 and len(X_test_3d) > 0:
        y_true_lstm, y_pred_lstm, t_lstm = train_lstm(
            X_train_3d, y_train_3d, X_val_3d, y_val_3d, X_test_3d, y_test_3d, input_dim)
        res = evaluate_model(y_true_lstm, y_pred_lstm, 'LSTM', n_features)
        res['耗时(s)'] = round(t_lstm, 1)
        all_overall.append(res)
        all_layered.extend(layered_evaluate(y_true_lstm, y_pred_lstm, lead_test_3d, 'LSTM', n_features))
        save_csv(all_overall, CSV_OVERALL)
        save_csv(all_layered, CSV_LAYERED)
        print(f"  → MAPE={res['MAPE']}%, MAE={res['MAE']}, RMSE={res['RMSE']}")
    else:
        print("  3D 数据不足，跳过 LSTM")

    overall_df = pd.DataFrame(all_overall).sort_values('MAPE').reset_index(drop=True)
    print("\n整体评估汇总（按MAPE升序）:")
    print(overall_df.to_string(index=False))

    layered_df = pd.DataFrame(all_layered)
    print("\n分层评估汇总:")
    for label in [lb for _, _, lb in LEAD_TIME_BINS]:
        sub = layered_df[layered_df['分层'] == label].sort_values('MAPE').reset_index(drop=True)
        print(f"  {label}")
        print(sub.to_string(index=False))

    best = overall_df.iloc[0]
    print(f"\n最优模型：{best['模型']}  MAPE={best['MAPE']}%")

    save_csv(all_overall, CSV_OVERALL)
    save_csv(all_layered, CSV_LAYERED)
    print(f"结果已保存: {CSV_OVERALL}, {CSV_LAYERED}")


if __name__ == '__main__':
    main()
