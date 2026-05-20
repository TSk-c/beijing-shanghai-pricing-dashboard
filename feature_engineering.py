# =====================================================
# feature_engineering.py
# 职责：数据加载 → 清洗 → 全部特征工程 → 保存
# 
# =====================================================
import os
os.environ['LOKY_MAX_CPU_COUNT'] = '4'
os.environ['JOBLIB_MULTIPROCESSING'] = '0'

import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import warnings

warnings.filterwarnings('ignore')

# =====================================================
# 1. 数据加载
# =====================================================
engine = create_engine('sqlite:///air_hsr_pricing.db')
fp = pd.read_sql('SELECT * FROM flight_prices', engine)
hsr = pd.read_sql('SELECT * FROM hsr_prices', engine)
expos = pd.read_sql('SELECT * FROM expos', engine)

fp['query_date'] = pd.to_datetime(fp['query_date']).dt.date
fp['dep_date'] = pd.to_datetime(fp['dep_date']).dt.date
hsr['query_date'] = pd.to_datetime(hsr['query_date']).dt.date
hsr['dep_date'] = pd.to_datetime(hsr['dep_date']).dt.date
expos['start_date'] = pd.to_datetime(expos['start_date']).dt.date
expos['end_date'] = pd.to_datetime(expos['end_date']).dt.date

print(f"航班价格记录：{fp.shape[0]} 条")
print(f"高铁聚合记录：{hsr.shape[0]} 条")
print(f"展会记录：{expos.shape[0]} 条")

# =====================================================
# 2. 节假日生命周期特征
# =====================================================
holiday_dates = sorted(fp[fp['is_holiday'] == 1]['dep_date'].unique())
holiday_ranges = []
if holiday_dates:
    start = holiday_dates[0]
    prev = holiday_dates[0]
    for d in holiday_dates[1:]:
        if (d - prev).days == 1:
            prev = d
        else:
            holiday_ranges.append((start, prev))
            start = prev = d
    holiday_ranges.append((start, prev))

def get_holiday_features(d):
    for s, e in holiday_ranges:
        if s <= d <= e:
            day_num = (d - s).days + 1
            length = (e - s).days + 1
            return pd.Series({
                'holiday_day_num': day_num,
                'is_holiday_mid': 1 if (2 <= day_num <= length - 2) else 0,
                'is_holiday_last_2d': 1 if day_num >= length - 1 else 0,
                'is_pre_holiday_peak': 0,
                'is_pre_holiday_buildup': 0,
                'is_post_holiday_dip': 0,
                'days_to_nearest_holiday': 0
            })
    is_pre_peak = 0; is_pre_buildup = 0; is_post_dip = 0; min_dist = 999
    for s, e in holiday_ranges:
        if d < s:
            db = (s - d).days
            min_dist = min(min_dist, db)
            if db == 1: is_pre_peak = 1
            elif db in [2, 3]: is_pre_buildup = 1
        elif d > e:
            da = (d - e).days
            min_dist = min(min_dist, da)
            if da == 1: is_post_dip = 1
    return pd.Series({
        'holiday_day_num': 0, 'is_holiday_mid': 0, 'is_holiday_last_2d': 0,
        'is_pre_holiday_peak': is_pre_peak, 'is_pre_holiday_buildup': is_pre_buildup,
        'is_post_holiday_dip': is_post_dip, 'days_to_nearest_holiday': min_dist
    })

holiday_feat_df = fp['dep_date'].apply(get_holiday_features)
fp = pd.concat([fp.reset_index(drop=True), holiday_feat_df.reset_index(drop=True)], axis=1)

# =====================================================
# 3. 时间特征
# =====================================================
fp['dep_dow'] = pd.to_datetime(fp['dep_date']).dt.weekday
fp['dep_time_hour'] = (
    pd.to_numeric(fp['dep_time'].str.split(':').str[0], errors='coerce') +
    pd.to_numeric(fp['dep_time'].str.split(':').str[1], errors='coerce') / 60
)

def period_auth(h):
    if pd.isna(h): return 5
    elif 7 <= h < 9: return 0
    elif 9 <= h < 12: return 1
    elif 12 <= h < 17: return 2
    elif 17 <= h < 20: return 3
    elif 20 <= h < 23: return 4
    else: return 5

fp['dep_period_enc'] = fp['dep_time_hour'].apply(period_auth)

# =====================================================
# 4. 高铁数据对齐
# =====================================================
hsr_max_query = hsr['query_date'].max()
hsr_min_query = hsr['query_date'].min()

fp['hsr_data_available'] = (
    (fp['days_prior'] <= 14) &
    (fp['query_date'] >= hsr_min_query) &
    (fp['query_date'] <= hsr_max_query)
).astype(int)

hsr_cols = ['query_date', 'dep_date', 'price_C', 'price_F', 'price_S',
            'remain_C', 'remain_F', 'remain_S', 'train_count', 'hsr_avg_duration_h']
fp = fp.merge(hsr[hsr_cols], on=['query_date', 'dep_date'], how='left')
for col in ['price_C', 'price_F', 'price_S', 'remain_C', 'remain_F', 'remain_S',
            'train_count', 'hsr_avg_duration_h']:
    fp[col] = fp[col].fillna(0)

# =====================================================
# 5. 展会特征
# =====================================================
from collections import defaultdict

date_max_scale = defaultdict(float)
for _, row in expos.iterrows():
    for d in pd.date_range(row['start_date'], row['end_date']).date:
        if row['scale_index'] > date_max_scale[d]:
            date_max_scale[d] = row['scale_index']
fp['expo_max_scale'] = fp['dep_date'].apply(lambda d: date_max_scale.get(d, 0.0))

expo_dates = set()
for _, row in expos.iterrows():
    for d in pd.date_range(row['start_date'], row['end_date']).date:
        expo_dates.add(d)
fp['is_expo_day'] = fp['dep_date'].apply(lambda d: 1 if d in expo_dates else 0)

# =====================================================
# 6. 辅助特征 & 分箱
# =====================================================
fp['duration_hours'] = fp['duration'] / 60
fp['days_prior_sq'] = fp['days_prior'] ** 2
fp['is_weekend'] = ((fp['dep_dow'] >= 5) & (fp['is_holiday'] == 0)).astype(int)

def assign_window(days):
    if days >= 15: return '远期(≥15天)'
    elif days >= 3: return '中期(3-14天)'
    else: return '临期(0-2天)'
fp['window'] = fp['days_prior'].apply(assign_window)

def assign_window_fine(days):
    if days <= 2: return '0-2天'
    elif days <= 7: return '3-7天'
    else: return '8-14天'
fp['window_fine'] = fp['days_prior'].apply(assign_window_fine)

fp['day_type'] = np.where((fp['is_weekend'] == 0) & (fp['is_holiday'] == 0), '工作日', '非工作日')

bins = [-1, 0, 2, 6, 13, 20, 30, 100]
labels = ['当天', '1-2天', '3-6天', '7-13天', '14-20天', '21-30天', '30天+']
fp['prior_bin'] = pd.cut(fp['days_prior'], bins=bins, labels=labels)

fp['prior_bin_heat'] = pd.cut(fp['days_prior'], bins=[-1, 2, 6, 13, 20, 30, 100],
                              labels=['0-2天', '3-6天', '7-13天', '14-20天', '21-30天', '30天+'])

# =====================================================
# 7. 高铁竞争特征重构
# =====================================================
print("\n>>> 构建竞争特征...")
hsr_mask = fp['hsr_data_available'] == 1

# --- 7.1 RPA（核心特征）---
fp['rpa_F'] = np.nan
fp.loc[hsr_mask, 'rpa_F'] = fp.loc[hsr_mask, 'price_F'] / fp.loc[hsr_mask, 'price']

fp['price_diff_F'] = np.nan
fp.loc[hsr_mask, 'price_diff_F'] = fp.loc[hsr_mask, 'price_F'] - fp.loc[hsr_mask, 'price']

# --- 7.2 供给紧张度（核心特征）---
fp['remain_F_rank'] = np.nan
fp.loc[hsr_mask, 'remain_F_rank'] = fp.loc[hsr_mask].groupby('days_prior')['remain_F'].transform(
    lambda x: x.rank(pct=True) if len(x) > 1 else 0.5
)
fp['supply_tension_F'] = 1 - fp['remain_F_rank']


# =====================================================
# 8. 交互特征构建
# =====================================================
print(">>> 构建交互特征...")

# 竞争 × 时间
fp['rpa_F_x_days_prior'] = fp['rpa_F'] * fp['days_prior']
fp['supply_tension_F_x_is_holiday'] = fp['supply_tension_F'] * fp['is_holiday']
fp['supply_tension_F_x_is_weekend'] = fp['supply_tension_F'] * fp['is_weekend']
fp['price_diff_F_x_days_prior'] = fp['price_diff_F'] * fp['days_prior']

# 竞争 × 场景
fp['rpa_F_x_is_weekend'] = fp['rpa_F'] * fp['is_weekend']

# 非线性/分段
fp['rpa_F_high'] = (fp['rpa_F'] > 1.2).astype(int)
fp['rpa_F_low'] = (fp['rpa_F'] < 0.8).astype(int)

tension_threshold = fp.loc[fp['hsr_data_available'] == 1, 'supply_tension_F'].quantile(0.8)
fp['supply_tension_high'] = (fp['supply_tension_F'] > tension_threshold).astype(int)

# 高铁内部交互
fp['hsr_F_S_spread'] = fp['price_F'] - fp['price_S']
fp['hsr_total_remain'] = fp['remain_C'] + fp['remain_F'] + fp['remain_S']

# RPA 分段（EDA用）
fp['rpa_segment'] = pd.cut(fp['rpa_F'],
                           bins=[0, 0.8, 1.0, 1.2, 1.5, 10],
                           labels=['高铁显著便宜', '高铁略便宜', '价格持平',
                                   '高铁略贵', '高铁显著贵'])

# =====================================================
# 9. 编码（建模用）
# =====================================================
fp['airline_enc'] = pd.Categorical(fp['airline']).codes
fp['dep_airport_enc'] = pd.Categorical(fp['dep_airport']).codes
fp['arr_airport_enc'] = pd.Categorical(fp['arr_airport']).codes

# =====================================================
# 10. 保存数据
# =====================================================
# 10.1 完整数据（供EDA使用）
fp.to_parquet('processed_data.parquet', index=False)

# 10.2 建模专用特征矩阵（供model.py使用）
model_features = [
    'flight_no', 'query_date', 'dep_date',
    'days_prior', 'days_prior_sq',
    'dep_dow', 'dep_time_hour', 'dep_period_enc',
    'is_weekend', 'is_holiday',
    'airline_enc', 'dep_airport_enc', 'arr_airport_enc',
    'duration_hours',
    'hsr_data_available',
    'price_C', 'price_F', 'price_S',
    'remain_C', 'remain_F', 'remain_S',
    'hsr_avg_duration_h', 'train_count',
    # ⭐ 核心竞争特征（3个）
    'rpa_F', 'price_diff_F', 'supply_tension_F',
    # ⭐ 交互特征
    'rpa_F_x_days_prior', 'supply_tension_F_x_is_holiday',
    'supply_tension_F_x_is_weekend', 'price_diff_F_x_days_prior',
    'rpa_F_x_is_weekend', 'rpa_F_high', 'rpa_F_low',
    'supply_tension_high', 'hsr_F_S_spread', 'hsr_total_remain',
    # 事件特征
    'expo_max_scale', 'is_expo_day',
    'is_pre_holiday_peak', 'is_pre_holiday_buildup',
    'holiday_day_num', 'is_holiday_mid', 'is_holiday_last_2d',
    'is_post_holiday_dip', 'days_to_nearest_holiday'
]

# 只保留实际存在的列
model_features = [c for c in model_features if c in fp.columns]
X = fp[model_features].copy()
y = fp[['price']].copy()

X.to_parquet('feature_matrix_final_v5.parquet', index=False)
y.to_parquet('target_final_v5.parquet', index=False)


print(f"   完整数据：processed_data.parquet ({fp.shape[0]}行, {fp.shape[1]}列)")
print(f"   建模特征：feature_matrix_final_v5.parquet ({X.shape[1]}列)")
print(f"   目标变量：target_final_v5.parquet")
print(f"   高铁有效覆盖率：{fp['hsr_data_available'].mean()*100:.1f}%")
print(f"   核心竞争特征：rpa_F | price_diff_F | supply_tension_F")

# In[]
# 查看processed_data.parquet情况

