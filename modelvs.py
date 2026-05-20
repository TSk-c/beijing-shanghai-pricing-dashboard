"""
============================================================
模型对比实验 — 基于文献方法
8:1:1 严格时间序划分 | 7 个模型 | MAPE 为主指标
============================================================
"""

import numpy as np
import pandas as pd
import os
import time
import json
import warnings
import inspect
warnings.filterwarnings('ignore')

from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from datetime import timedelta

import xgboost as xgb

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

RANDOM_STATE = 42
OUTPUT_DIR = 'output_model_vs'
SEQ_LEN = 7
np.random.seed(RANDOM_STATE)
torch.manual_seed(RANDOM_STATE)

os.makedirs(OUTPUT_DIR, exist_ok=True)

CSV_PATH = os.path.join(OUTPUT_DIR, 'model_comparison_results.csv')


def save_incremental(all_results):
    df = pd.DataFrame(all_results)
    df = df.sort_values('MAPE').reset_index(drop=True)
    df.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')


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
    }


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
    train_end = query_dates[int(n_dates * 0.8)]
    val_end = query_dates[int(n_dates * 0.9)]

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
    X_train = pd.DataFrame(imputer.fit_transform(X_train), columns=model_features, index=X_train.index)
    X_val = pd.DataFrame(imputer.transform(X_val), columns=model_features, index=X_val.index)
    X_test = pd.DataFrame(imputer.transform(X_test), columns=model_features, index=X_test.index)

    print(f"\n  时间划分（8:1:1 按 query_date）：")
    print(f"    训练集：~ 至 {train_end}，{len(X_train)} 条")
    print(f"    验证集：{query_dates[int(n_dates * 0.8) + 1]} ~ {val_end}，{len(X_val)} 条")
    print(f"    测试集：{query_dates[int(n_dates * 0.9) + 1]} ~ {query_dates[-1]}，{len(X_test)} 条")

    assert query_dates[int(n_dates * 0.9) + 1] > val_end, "测试集起始日期必须 > 验证集结束日期"
    assert val_end > train_end, "验证集结束日期必须 > 训练集结束日期"

    meta = {
        'df': df, 'model_features': model_features, 'n_features': n_features,
        'train_mask': train_mask, 'val_mask': val_mask, 'test_mask': test_mask,
    }
    return X_train, y_train, X_val, y_val, X_test, y_test, meta


def build_3d_data(df, model_features, split_mask, seq_len=SEQ_LEN):
    sub = df.loc[split_mask].copy()
    sub = sub.sort_values(['flight_no', 'query_date', 'dep_date', 'days_prior'])
    X_list, y_list = [], []
    for _fn, grp in sub.groupby('flight_no'):
        if len(grp) < seq_len:
            continue
        feat = grp[model_features].values.astype(np.float32)
        prices = grp['price'].values.astype(np.float32)
        for i in range(len(grp) - seq_len + 1):
            X_list.append(feat[i:i + seq_len])
            y_list.append(prices[i + seq_len - 1])
    if not X_list:
        return np.array([]), np.array([])
    return np.stack(X_list), np.array(y_list)


# ============================================================
# 模型 1：随机森林
# ============================================================

def train_rf(X_train, y_train, X_test, y_test, n_features):
    print("\n[1/7] 随机森林...")
    t0 = time.time()
    rf = RandomForestRegressor(
        n_estimators=200, max_depth=10, min_samples_split=5,
        n_jobs=-1, random_state=RANDOM_STATE,
    )
    rf.fit(X_train, y_train)
    y_pred = rf.predict(X_test)
    elapsed = time.time() - t0
    print(f"  RF 完成，耗时 {elapsed:.1f}s")
    return y_test.values, y_pred, elapsed


# ============================================================
# 模型 2：XGBoost
# ============================================================

def train_xgb(X_train, y_train, X_val, y_val, X_test, y_test, n_features):
    print("\n[2/7] XGBoost（验证集早停）...")
    t0 = time.time()
    model = xgb.XGBRegressor(
        n_estimators=2000,
        early_stopping_rounds=50,
        eval_metric='rmse',
        objective='reg:squarederror',
        learning_rate=0.03,
        max_depth=8,
        subsample=0.8,
        colsample_bytree=0.7,
        reg_alpha=0.1,
        reg_lambda=0.3,
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
# 深度学习通用训练
# ============================================================

def train_deep_model(model, X_train_3d, y_train_3d, X_val_3d, y_val_3d,
                     epochs=20, batch_size=256, lr=1e-3, patience=5, device='cpu'):
    model = model.to(device)
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    train_ds = TensorDataset(
        torch.FloatTensor(X_train_3d),
        torch.FloatTensor(y_train_3d),
    )
    val_ds = TensorDataset(
        torch.FloatTensor(X_val_3d),
        torch.FloatTensor(y_val_3d),
    )
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
# 模型 3：LSTM
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
    print("\n[3/7] LSTM（隐藏层 64→32，Dropout=0.1）...")
    t0 = time.time()
    model = LSTMModel(input_dim)
    model = train_deep_model(model, X_train_3d, y_train_3d, X_val_3d, y_val_3d,
                             epochs=20, batch_size=256, lr=1e-3, patience=5)
    model.eval()
    with torch.no_grad():
        y_pred = model(torch.FloatTensor(X_test_3d)).squeeze().numpy()
    elapsed = time.time() - t0
    print(f"  LSTM 完成，耗时 {elapsed:.1f}s")
    return y_test_3d, y_pred, elapsed


# ============================================================
# 模型 4：BiLSTM
# ============================================================

class BiLSTMModel(nn.Module):
    def __init__(self, input_dim, hidden1=64, hidden2=32, dropout=0.1):
        super().__init__()
        self.bilstm = nn.LSTM(input_dim, hidden1, batch_first=True, bidirectional=True)
        self.drop1 = nn.Dropout(dropout)
        self.lstm2 = nn.LSTM(hidden1 * 2, hidden2, batch_first=True)
        self.drop2 = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden2, 1)

    def forward(self, x):
        out, _ = self.bilstm(x)
        out = self.drop1(out)
        out, _ = self.lstm2(out)
        out = self.drop2(out[:, -1, :])
        return self.fc(out)


def train_bilstm(X_train_3d, y_train_3d, X_val_3d, y_val_3d, X_test_3d, y_test_3d, input_dim):
    print("\n[4/7] BiLSTM（Bidirectional LSTM 64 → LSTM 32）...")
    t0 = time.time()
    model = BiLSTMModel(input_dim)
    model = train_deep_model(model, X_train_3d, y_train_3d, X_val_3d, y_val_3d,
                             epochs=20, batch_size=256, lr=1e-3, patience=5)
    model.eval()
    with torch.no_grad():
        y_pred = model(torch.FloatTensor(X_test_3d)).squeeze().numpy()
    elapsed = time.time() - t0
    print(f"  BiLSTM 完成，耗时 {elapsed:.1f}s")
    return y_test_3d, y_pred, elapsed


# ============================================================
# 模型 5：GRU
# ============================================================

class GRUModel(nn.Module):
    def __init__(self, input_dim, hidden1=64, hidden2=32, dropout=0.1):
        super().__init__()
        self.gru1 = nn.GRU(input_dim, hidden1, batch_first=True)
        self.drop1 = nn.Dropout(dropout)
        self.gru2 = nn.GRU(hidden1, hidden2, batch_first=True)
        self.drop2 = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden2, 1)

    def forward(self, x):
        out, _ = self.gru1(x)
        out = self.drop1(out)
        out, _ = self.gru2(out)
        out = self.drop2(out[:, -1, :])
        return self.fc(out)


def train_gru(X_train_3d, y_train_3d, X_val_3d, y_val_3d, X_test_3d, y_test_3d, input_dim):
    print("\n[5/7] GRU（隐藏层 64→32，Dropout=0.1）...")
    t0 = time.time()
    model = GRUModel(input_dim)
    model = train_deep_model(model, X_train_3d, y_train_3d, X_val_3d, y_val_3d,
                             epochs=20, batch_size=256, lr=1e-3, patience=5)
    model.eval()
    with torch.no_grad():
        y_pred = model(torch.FloatTensor(X_test_3d)).squeeze().numpy()
    elapsed = time.time() - t0
    print(f"  GRU 完成，耗时 {elapsed:.1f}s")
    return y_test_3d, y_pred, elapsed


# ============================================================
# 模型 6：Transformer
# ============================================================

class TransformerModel(nn.Module):
    def __init__(self, input_dim, d_model=64, nhead=1, dropout=0.1):
        super().__init__()
        self.input_proj = nn.Linear(input_dim, d_model)
        self.pos_enc = nn.Parameter(torch.randn(1, SEQ_LEN, d_model) * 0.1)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead, dim_feedforward=d_model * 4,
            dropout=dropout, batch_first=True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=2)
        self.fc = nn.Linear(d_model, 1)

    def forward(self, x):
        x = self.input_proj(x) + self.pos_enc
        x = self.encoder(x)
        return self.fc(x[:, -1, :])


def train_transformer(X_train_3d, y_train_3d, X_val_3d, y_val_3d, X_test_3d, y_test_3d, input_dim):
    print("\n[6/7] Transformer（隐藏层 64，注意力头数 1）...")
    t0 = time.time()
    model = TransformerModel(input_dim)
    model = train_deep_model(model, X_train_3d, y_train_3d, X_val_3d, y_val_3d,
                             epochs=20, batch_size=256, lr=1e-3, patience=5)
    model.eval()
    with torch.no_grad():
        y_pred = model(torch.FloatTensor(X_test_3d)).squeeze().numpy()
    elapsed = time.time() - t0
    print(f"  Transformer 完成，耗时 {elapsed:.1f}s")
    return y_test_3d, y_pred, elapsed


# ============================================================
# 模型 7：DP-CUSUM-TFT
# ============================================================

def train_tft(df, model_features, train_mask, val_mask, test_mask):
    print("\n[7/7] DP-CUSUM-TFT（pytorch-forecasting）...")
    t0 = time.time()

    try:
        from pytorch_forecasting import TimeSeriesDataSet, TemporalFusionTransformer
        from pytorch_forecasting.data import GroupNormalizer
        from lightning.pytorch import Trainer
        from lightning.pytorch.callbacks import EarlyStopping
        import pytorch_forecasting.metrics as ptf_metrics
    except ImportError as e:
        print(f"  跳过 TFT：缺少依赖 {e}")
        return None, None, 0

    all_data = df.copy()
    all_data = all_data.sort_values(['flight_no', 'query_date']).reset_index(drop=True)
    all_data['time_idx'] = all_data.groupby('flight_no').cumcount()

    static_cols = [c for c in ['airline_enc', 'dep_airport_enc', 'arr_airport_enc', 'is_weekend'] if c in all_data.columns]
    known_future = [c for c in ['days_prior', 'dep_dow'] if c in all_data.columns]
    observed = [c for c in model_features if c not in static_cols and c not in known_future]

    all_data[static_cols] = all_data[static_cols].astype(str)
    all_data['flight_no'] = all_data['flight_no'].astype(str)

    query_dates = sorted(all_data['query_date'].unique())
    n_dates = len(query_dates)
    train_end_date = query_dates[int(n_dates * 0.8)]
    val_end_date = query_dates[int(n_dates * 0.9)]

    train_data = all_data[all_data['query_date'] <= train_end_date].copy()
    val_data = all_data[(all_data['query_date'] > train_end_date) & (all_data['query_date'] <= val_end_date)].copy()
    test_data_raw = all_data[all_data['query_date'] > val_end_date].copy()

    all_cat_cols = static_cols + ['flight_no']
    for col in all_cat_cols:
        train_cats = set(train_data[col].unique())
        val_cats = set(val_data[col].unique())
        test_cats = set(test_data_raw[col].unique())
        unknown_val = '__UNKNOWN__'
        for cat in (val_cats | test_cats) - train_cats:
            val_data[col] = val_data[col].replace(cat, unknown_val)
            test_data_raw[col] = test_data_raw[col].replace(cat, unknown_val)
        if unknown_val not in train_cats and ((val_cats | test_cats) - train_cats):
            sample_row = train_data.iloc[0:1].copy()
            sample_row[col] = unknown_val
            train_data = pd.concat([train_data, sample_row], ignore_index=True)

    max_encoder_length = 7
    max_decoder_length = 7

    all_flights = set(train_data['flight_no'].unique()) & set(val_data['flight_no'].unique()) & set(test_data_raw['flight_no'].unique())
    print(f"  训练/验证/测试共同航班数: {len(all_flights)}")
    train_data_sampled = train_data[train_data['flight_no'].isin(all_flights)].copy().reset_index(drop=True)
    val_data_sampled = val_data[val_data['flight_no'].isin(all_flights)].copy().reset_index(drop=True)
    test_data_sampled = test_data_raw[test_data_raw['flight_no'].isin(all_flights)].copy().reset_index(drop=True)
    print(f"  TFT 全航班训练 (train={len(train_data_sampled)}, val={len(val_data_sampled)}, test={len(test_data_sampled)})")

    try:
        training_ds = TimeSeriesDataSet(
            train_data_sampled,
            time_idx='time_idx',
            target='price',
            group_ids=['flight_no'],
            min_encoder_length=max_encoder_length // 2,
            max_encoder_length=max_encoder_length,
            min_prediction_length=1,
            max_prediction_length=max_decoder_length,
            static_categoricals=static_cols,
            time_varying_known_reals=known_future,
            time_varying_unknown_reals=observed + ['price'],
            target_normalizer=GroupNormalizer(groups=['flight_no'], transformation='softplus'),
            add_relative_time_idx=True,
            add_target_scales=True,
            add_encoder_length=True,
            allow_missing_timesteps=True,
        )

        val_ds = TimeSeriesDataSet.from_dataset(training_ds, pd.concat([train_data_sampled, val_data_sampled], ignore_index=True),
                                                 predict=True, stop_randomization=True)

        train_loader = training_ds.to_dataloader(train=True, batch_size=1024, num_workers=0)
        val_loader = val_ds.to_dataloader(train=False, batch_size=1024, num_workers=0)

        tft_model = TemporalFusionTransformer.from_dataset(
            training_ds,
            hidden_size=32,
            attention_head_size=1,
            dropout=0.1,
            learning_rate=0.01,
            output_size=7,
            loss=ptf_metrics.QuantileLoss(),
        )

        early_stop = EarlyStopping(monitor='val_loss', patience=3, mode='min')
        trainer = Trainer(
            max_epochs=8,
            accelerator='cpu',
            gradient_clip_val=0.1,
            callbacks=[early_stop],
            enable_progress_bar=True,
            logger=False,
        )
        trainer.fit(tft_model, train_dataloaders=train_loader, val_dataloaders=val_loader)

        test_data = test_data_sampled.copy()
        test_data = test_data.reset_index(drop=True)
        try:
            test_ds = TimeSeriesDataSet.from_dataset(training_ds, test_data,
                                                      predict=True, stop_randomization=True)
        except Exception:
            combined = pd.concat([train_data_sampled, val_data_sampled, test_data], ignore_index=True)
            test_ds = TimeSeriesDataSet.from_dataset(training_ds, combined,
                                                      predict=True, stop_randomization=True)
        test_loader = test_ds.to_dataloader(train=False, batch_size=512, num_workers=0)

        raw_pred = tft_model.predict(test_loader, mode='prediction', return_index=True,
                                      trainer_kwargs=dict(accelerator='cpu', enable_progress_bar=False))
        if isinstance(raw_pred, (tuple, list)):
            predictions = raw_pred[0]
        else:
            predictions = raw_pred
        y_pred = predictions.cpu().numpy().flatten()

        y_true = test_data_sampled['price'].values[:len(y_pred)]

        valid_mask = ~(np.isnan(y_true) | np.isnan(y_pred) | np.isinf(y_true) | np.isinf(y_pred))
        y_true = y_true[valid_mask]
        y_pred = y_pred[valid_mask]
        print(f"  TFT 预测有效样本数: {len(y_true)} (过滤 NaN/Inf 后)")

        min_len = min(len(y_true), len(y_pred))
        elapsed = time.time() - t0
        print(f"  TFT 完成，耗时 {elapsed:.1f}s")
        return y_true[:min_len], y_pred[:min_len], elapsed

    except Exception as e:
        import traceback
        elapsed = time.time() - t0
        print(f"  TFT 训练出错：{e}")
        traceback.print_exc()
        print(f"  跳过 TFT，耗时 {elapsed:.1f}s")
        return None, None, elapsed


# ============================================================
# 主流程
# ============================================================

def main():
    print("=" * 60)
    print("模型对比实验（8:1:1 时间序划分 + 7 模型 | MAPE 主指标）")
    print("=" * 60)

    X_train, y_train, X_val, y_val, X_test, y_test, meta = load_and_split()
    df = meta['df']
    model_features = meta['model_features']
    n_features = meta['n_features']
    train_mask = meta['train_mask']
    val_mask = meta['val_mask']
    test_mask = meta['test_mask']

    all_results = []

    # --- RF ---
    y_true_rf, y_pred_rf, t_rf = train_rf(X_train, y_train, X_test, y_test, n_features)
    res = evaluate_model(y_true_rf, y_pred_rf, '随机森林', n_features)
    res['耗时(s)'] = round(t_rf, 1)
    all_results.append(res)
    save_incremental(all_results)
    print(f"  → MAPE={res['MAPE']}%, MAE={res['MAE']}, RMSE={res['RMSE']}")

    # --- XGBoost ---
    y_true_xgb, y_pred_xgb, t_xgb = train_xgb(X_train, y_train, X_val, y_val, X_test, y_test, n_features)
    res = evaluate_model(y_true_xgb, y_pred_xgb, 'XGBoost', n_features)
    res['耗时(s)'] = round(t_xgb, 1)
    all_results.append(res)
    save_incremental(all_results)
    print(f"  → MAPE={res['MAPE']}%, MAE={res['MAE']}, RMSE={res['RMSE']}")

    # --- 3D 数据转换 ---
    print("\n构建三维滑动窗口数据（序列长度=7）...")
    X_train_3d, y_train_3d = build_3d_data(df, model_features, train_mask)
    X_val_3d, y_val_3d = build_3d_data(df, model_features, val_mask)
    X_test_3d, y_test_3d = build_3d_data(df, model_features, test_mask)
    input_dim = X_train_3d.shape[2] if len(X_train_3d) > 0 else n_features
    print(f"  训练 3D: {X_train_3d.shape}, 验证 3D: {X_val_3d.shape}, 测试 3D: {X_test_3d.shape}")

    if len(X_train_3d) > 0 and len(X_val_3d) > 0 and len(X_test_3d) > 0:
        # --- LSTM ---
        y_true_lstm, y_pred_lstm, t_lstm = train_lstm(
            X_train_3d, y_train_3d, X_val_3d, y_val_3d, X_test_3d, y_test_3d, input_dim)
        res = evaluate_model(y_true_lstm, y_pred_lstm, 'LSTM', n_features)
        res['耗时(s)'] = round(t_lstm, 1)
        all_results.append(res)
        save_incremental(all_results)
        print(f"  → MAPE={res['MAPE']}%, MAE={res['MAE']}, RMSE={res['RMSE']}")

        # --- BiLSTM ---
        y_true_bilstm, y_pred_bilstm, t_bilstm = train_bilstm(
            X_train_3d, y_train_3d, X_val_3d, y_val_3d, X_test_3d, y_test_3d, input_dim)
        res = evaluate_model(y_true_bilstm, y_pred_bilstm, 'BiLSTM', n_features)
        res['耗时(s)'] = round(t_bilstm, 1)
        all_results.append(res)
        save_incremental(all_results)
        print(f"  → MAPE={res['MAPE']}%, MAE={res['MAE']}, RMSE={res['RMSE']}")

        # --- GRU ---
        y_true_gru, y_pred_gru, t_gru = train_gru(
            X_train_3d, y_train_3d, X_val_3d, y_val_3d, X_test_3d, y_test_3d, input_dim)
        res = evaluate_model(y_true_gru, y_pred_gru, 'GRU', n_features)
        res['耗时(s)'] = round(t_gru, 1)
        all_results.append(res)
        save_incremental(all_results)
        print(f"  → MAPE={res['MAPE']}%, MAE={res['MAE']}, RMSE={res['RMSE']}")

        # --- Transformer ---
        y_true_tf, y_pred_tf, t_tf = train_transformer(
            X_train_3d, y_train_3d, X_val_3d, y_val_3d, X_test_3d, y_test_3d, input_dim)
        res = evaluate_model(y_true_tf, y_pred_tf, 'Transformer', n_features)
        res['耗时(s)'] = round(t_tf, 1)
        all_results.append(res)
        save_incremental(all_results)
        print(f"  → MAPE={res['MAPE']}%, MAE={res['MAE']}, RMSE={res['RMSE']}")
    else:
        print("  3D 数据不足，跳过深度学习模型")

    # --- TFT ---
    y_true_tft, y_pred_tft, t_tft = train_tft(df, model_features, train_mask, val_mask, test_mask)
    if y_true_tft is not None and y_pred_tft is not None and len(y_true_tft) > 0:
        res = evaluate_model(y_true_tft, y_pred_tft, 'DP-CUSUM-TFT(全航班)', n_features)
        res['耗时(s)'] = round(t_tft, 1)
        all_results.append(res)
        save_incremental(all_results)
        print(f"  → MAPE={res['MAPE']}%, MAE={res['MAE']}, RMSE={res['RMSE']}")

    # --- 汇总 ---
    results_df = pd.DataFrame(all_results)
    results_df = results_df.sort_values('MAPE').reset_index(drop=True)

    print("\n" + "=" * 80)
    print("模型对比汇总（按 MAPE 升序排列，MAPE 为主指标）")
    print("=" * 80)
    print(results_df.to_string(index=False))

    best = results_df.iloc[0]
    print(f"\n最优模型：{best['模型']}  MAPE={best['MAPE']}%  MAE={best['MAE']}  RMSE={best['RMSE']}")

    save_incremental(all_results)
    print(f"\n结果已保存至: {CSV_PATH}")
    print("=" * 80)


if __name__ == '__main__':
    import sys
    if '--tft-only' in sys.argv:
        print("=" * 60)
        print("仅运行 TFT 模型")
        print("=" * 60)
        X_train, y_train, X_val, y_val, X_test, y_test, meta = load_and_split()
        df = meta['df']
        model_features = meta['model_features']
        n_features = meta['n_features']
        train_mask = meta['train_mask']
        val_mask = meta['val_mask']
        test_mask = meta['test_mask']
        y_true_tft, y_pred_tft, t_tft = train_tft(df, model_features, train_mask, val_mask, test_mask)
        if y_true_tft is not None and y_pred_tft is not None and len(y_true_tft) > 0:
            try:
                res = evaluate_model(y_true_tft, y_pred_tft, 'DP-CUSUM-TFT(全航班)', n_features)
                res['耗时(s)'] = round(t_tft, 1)
                print(f"  → MAPE={res['MAPE']}%, MAE={res['MAE']}, RMSE={res['RMSE']}")
                existing = pd.read_csv(CSV_PATH) if os.path.exists(CSV_PATH) else pd.DataFrame()
                all_results = existing.to_dict('records') if len(existing) > 0 else []
                all_results.append(res)
                save_incremental(all_results)
                results_df = pd.DataFrame(all_results).sort_values('MAPE').reset_index(drop=True)
                print("\n" + results_df.to_string(index=False))
            except Exception as e2:
                import traceback
                print(f"  评估出错：{e2}")
                traceback.print_exc()
        else:
            print("TFT 训练失败")
    else:
        main()
