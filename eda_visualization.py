# =====================================================
# eda_visualization.py
# 职责：读取 processed_data.parquet → 纯可视化 & 分析
# 运行：python eda_visualization.py
# 依赖：必须先运行 feature_engineering.py
# =====================================================
# In[]
import os
os.environ['LOKY_MAX_CPU_COUNT'] = '4'
os.environ['JOBLIB_MULTIPROCESSING'] = '0'

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import pearsonr, ttest_ind
import matplotlib.dates as mdates
from matplotlib.patches import Patch
import statsmodels.api as sm
from scipy import stats
from datetime import timedelta
import warnings

warnings.filterwarnings('ignore')

# =====================================================
# 1. 样式配置
# =====================================================
COLORS = {
    'main': '#2C3E50', 'sub1': '#C0392B', 'sub2': '#16A085',
    'sub3': '#2980B9', 'sub4': '#8E44AD', 'sub5': '#F39C12',
    'gray_light': '#F2F3F4', 'gray_mid': '#B2BABB', 'gray_dark': '#566573',
    'palette': ['#2C3E50', '#C0392B', '#16A085', '#2980B9', '#8E44AD', '#F39C12']
}

plt.rcParams.update({
    'font.family': ['Arial', 'SimHei'], 'font.size': 8, 'axes.titlesize': 9,
    'axes.labelsize': 8, 'xtick.labelsize': 7, 'ytick.labelsize': 7,
    'legend.fontsize': 7, 'figure.dpi': 300, 'savefig.dpi': 300,
    'axes.linewidth': 0.6, 'xtick.major.width': 0.6, 'ytick.major.width': 0.6,
    'xtick.major.size': 3, 'ytick.major.size': 3,
    'axes.edgecolor': COLORS['gray_dark'], 'axes.labelcolor': COLORS['main'],
    'text.color': COLORS['main'], 'xtick.color': COLORS['gray_dark'],
    'ytick.color': COLORS['gray_dark'], 'figure.facecolor': 'white',
    'axes.facecolor': 'white', 'grid.color': COLORS['gray_mid'],
    'grid.linewidth': 0.4, 'grid.alpha': 0.5,
})

def despine(ax):
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_linewidth(0.6)
    ax.spines['bottom'].set_linewidth(0.6)

# =====================================================
# 2. 读取数据
# =====================================================
print(">>> 读取 processed_data.parquet...")
fp = pd.read_parquet('processed_data.parquet')

min_date = fp['dep_date'].min()
max_date = fp['dep_date'].max()
hsr_mask = fp['hsr_data_available'] == 1

print(f"数据范围：{min_date} 至 {max_date}")
print(f"总记录：{len(fp)} | 高铁有效：{hsr_mask.sum()}")

# =====================================================
# 3. 辅助函数 & 常量（从 dep_date 重新计算节假日）
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

def merge_ranges(dates_list):
    if not dates_list:
        return []
    ranges = []
    start = prev = dates_list[0]
    for d in dates_list[1:]:
        if (d - prev).days == 1:
            prev = d
        else:
            ranges.append((start, prev))
            start = prev = d
    ranges.append((start, prev))
    return ranges

all_dates = sorted(fp['dep_date'].unique())
weekend_dates = [d for d in all_dates if pd.to_datetime(d).weekday() >= 5]
holiday_set = set()
for s, e in holiday_ranges:
    for d in pd.date_range(s, e).date:
        holiday_set.add(d)
weekend_dates = [d for d in weekend_dates if d not in holiday_set]

def draw_weekend_holiday_shading(ax, date_min, date_max):
    wk_dates = [d for d in weekend_dates if date_min <= d <= date_max]
    for start, end in merge_ranges(wk_dates):
        ax.axvspan(start, end, facecolor='#a8d8ea', alpha=0.25, zorder=1,
                   edgecolor='#5dacbd', linewidth=1.0)
    for s, e in holiday_ranges:
        start_eff = max(s, date_min)
        end_eff = min(e, date_max)
        if start_eff <= end_eff:
            ax.axvspan(start_eff, end_eff, facecolor='#ffd3b6', alpha=0.35, zorder=1,
                       edgecolor='#ff9a76', linewidth=1.0)

weekend_patch = Patch(facecolor='#a8d8ea', alpha=0.4, edgecolor='#5dacbd', linewidth=1.5, label='周末')
holiday_patch = Patch(facecolor='#ffd3b6', alpha=0.5, edgecolor='#ff9a76', linewidth=1.5, label='节假日')

# =====================================================
# E1: 票价分布
# =====================================================
fig, ax = plt.subplots(figsize=(7, 4))
sns.histplot(fp['price'], bins=80, kde=True, ax=ax, color=COLORS['main'],
             edgecolor='white', linewidth=0.3, alpha=0.85, stat='density')
for line in ax.lines:
    line.set_color(COLORS['sub1'])
    line.set_linewidth(1.5)
ax.axvline(fp['price'].median(), color=COLORS['sub3'], linestyle='--', linewidth=1.0,
           label=f"中位数={fp['price'].median():.0f}元")
ax.axvline(fp['price'].mean(), color=COLORS['main'], linestyle='--', linewidth=1.0,
           label=f"均值={fp['price'].mean():.0f}元")
ax.set_title('京沪航线经济舱票价分布（核密度估计）', fontweight='bold', pad=10)
ax.set_xlabel('票价（元）')
ax.set_ylabel('密度')
ax.legend(frameon=False, loc='upper right')
despine(ax)
plt.tight_layout()
plt.show()

print(f"\n票价分布：偏度={stats.skew(fp['price']):.2f}，峰度={stats.kurtosis(fp['price']):.2f}")

# =====================================================
# E2: 提前天数结构性分析
# =====================================================
# E2-1 典型出发日期预订曲线
typical_dates = []
wednesdays = sorted(set(fp[(fp['dep_dow'] == 2) & (fp['is_holiday'] == 0) &
                           (fp['is_pre_holiday_peak'] == 0) & (fp['is_expo_day'] == 0)]['dep_date']))
if wednesdays:
    typical_dates.append(('普通周三', wednesdays[0]))

preferred_friday = pd.Timestamp('2026-04-24').date()
if preferred_friday in fp['dep_date'].values:
    typical_dates.append(('周五', preferred_friday))
else:
    fridays_all = sorted(set(fp[(fp['dep_dow'] == 4) & (fp['is_holiday'] == 0) &
                                (fp['is_pre_holiday_peak'] == 0)]['dep_date']))
    friday_stats = [(d, fp[fp['dep_date']==d]['days_prior'].max(), len(fp[fp['dep_date']==d]))
                    for d in fridays_all]
    good = [(d, m, n) for d, m, n in friday_stats if m >= 14 and n >= 20]
    if good:
        chosen = sorted(good, key=lambda x: x[0])[len(good)//2][0]
        typical_dates.append(('周五', chosen))

pre_peak = sorted(set(fp[fp['is_pre_holiday_peak'] == 1]['dep_date']))
if pre_peak:
    typical_dates.append(('节假日前1天', pre_peak[0]))

holiday_mid = sorted(set(fp[fp['is_holiday_mid'] == 1]['dep_date']))
if holiday_mid:
    typical_dates.append(('节假日中', holiday_mid[0]))

if holiday_ranges:
    last_holiday_dates = [e for s, e in holiday_ranges]
    available_last = sorted(set(d for d in last_holiday_dates
                                if d >= min_date and d <= max_date and d in fp['dep_date'].values))
    if available_last:
        typical_dates.append(('节假日最后一天', available_last[0]))

fig, ax = plt.subplots(figsize=(8, 4.5))
for label, d in typical_dates:
    sub = fp[fp['dep_date'] == d].groupby('days_prior')['price'].mean().sort_index()
    ax.plot(sub.index, sub.values, 'o-', markersize=3, linewidth=1.2, label=f'{label} ({d})')
for d_line, lab in zip([14, 7, 3, 1], ['14天','7天','3天','1天']):
    ax.axvline(d_line, color=COLORS['gray_dark'], linestyle='--', alpha=0.4, linewidth=0.8)
    ax.text(d_line, ax.get_ylim()[1]*0.95, lab, color=COLORS['gray_dark'], fontsize=7, ha='center')
ax.set_title('典型出发日期的预订曲线（单日期，避免混叠）', fontweight='bold')
ax.set_xlabel('提前天数（天）'); ax.set_ylabel('平均票价（元）')
ax.set_xlim(0, 30); ax.legend(loc='upper right', fontsize=6.5, frameon=False); despine(ax)
plt.tight_layout(); plt.show()

# E2-2 分位数扩散
fig, ax = plt.subplots(figsize=(7.08, 3.5))
for q, color, alpha, lw, label in [
    (0.1, COLORS['sub2'], 0.4, 0.8, '10%分位数'),
    (0.25, COLORS['sub3'], 0.6, 1.0, '25%分位数'),
    (0.5, COLORS['main'], 1.0, 1.8, '中位数'),
    (0.75, COLORS['sub3'], 0.6, 1.0, '75%分位数'),
    (0.9, COLORS['sub2'], 0.4, 0.8, '90%分位数')
]:
    curve = fp[fp['days_prior'] <= 30].groupby('days_prior')['price'].quantile(q)
    ax.plot(curve.index, curve.values, color=color, linewidth=lw, alpha=alpha, label=label)
for d, lab in zip([14, 7, 3, 1], ['14天', '7天', '3天', '1天']):
    ax.axvline(d, color=COLORS['gray_dark'], linestyle='--', alpha=0.4, linewidth=0.8)
    ax.text(d, ax.get_ylim()[1]*0.97, lab, color=COLORS['gray_dark'], fontsize=7, ha='center')
ax.set_title('票价分位数随提前天数的变化（0-30天）', fontweight='bold')
ax.set_xlabel('提前天数（天）'); ax.set_ylabel('经济舱票价（元）')
ax.set_xlim(0, 30); ax.legend(loc='upper right', fontsize=6.5, ncol=3, frameon=True, fancybox=False, edgecolor=COLORS['gray_mid'])
despine(ax); plt.tight_layout(); plt.show()

# E2-3 关键区间箱线图
fig, ax = plt.subplots(figsize=(7.08, 3.5))
order = ['当天', '1-2天', '3-6天', '7-13天', '14-20天', '21-30天', '30天+']
sns.boxplot(x='prior_bin', y='price', data=fp, order=order, ax=ax,
            palette=[COLORS['main']]*len(order), width=0.5,
            boxprops=dict(alpha=0.8), medianprops=dict(color=COLORS['sub1'], linewidth=1.5),
            whiskerprops=dict(color=COLORS['gray_dark'], linewidth=0.8),
            capprops=dict(color=COLORS['gray_dark'], linewidth=0.8),
            flierprops=dict(marker='o', markerfacecolor=COLORS['gray_mid'], markeredgecolor='none', markersize=2, alpha=0.5))
ax.axhline(fp['price'].median(), color=COLORS['sub1'], linestyle='--', alpha=0.8, linewidth=1.0, label='全样本中位数')
ax.set_title('不同提前天区间的经济舱票价分布', fontweight='bold')
ax.set_xlabel('提前天数区间'); ax.set_ylabel('票价（元）')
ax.legend(loc='upper right', frameon=True, fancybox=False, edgecolor=COLORS['gray_mid'])
despine(ax); plt.tight_layout(); plt.show()

# =====================================================
# E3: 航司预订曲线 + 周内效应热力图
# =====================================================
airlines = sorted(fp['airline'].unique())
cmap = plt.cm.tab20
airline_color_map = {a: cmap(i % 20) for i, a in enumerate(airlines)}

fig, ax = plt.subplots(figsize=(10, 4.5))
np.random.seed(42)
sample = fp[fp['days_prior'] <= 30].sample(min(5000, len(fp)))
ax.scatter(sample['days_prior'], sample['price'], color=COLORS['gray_mid'], alpha=0.15, s=3, edgecolors='none')
for airline in airlines:
    trend = fp[(fp['airline'] == airline) & (fp['days_prior'] <= 30)].groupby('days_prior')['price'].mean().sort_index()
    if len(trend) > 0:
        ax.plot(trend.index, trend.values, linewidth=1.2, color=airline_color_map[airline], label=airline)
for d, lab, ls in zip([14, 7, 3, 1], ['14天', '7天', '3天', '1天'], ['--', '--', ':', ':']):
    ax.axvline(d, color=COLORS['sub1'], linestyle=ls, alpha=0.4, linewidth=0.8)
    ax.text(d, ax.get_ylim()[1]*0.97, lab, color=COLORS['sub1'], fontsize=7, ha='center', va='top',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='white', edgecolor='none', alpha=0.9))
ax.set_title('各航司票价随提前天数变化（0-30天）', fontweight='bold')
ax.set_xlabel('提前天数（天）'); ax.set_ylabel('经济舱票价（元）')
ax.set_xlim(0, 30)
ax.legend(loc='upper right', fontsize=6.5, ncol=2, frameon=True, fancybox=False, edgecolor=COLORS['gray_mid'])
despine(ax); plt.tight_layout(); plt.show()

# E3-2 热力图
pivot_weekday = fp.groupby(['dep_dow', 'prior_bin_heat'])['price'].mean().unstack()
pivot_weekday.index = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
fig, ax = plt.subplots(figsize=(7.5, 3.8))
sns.heatmap(pivot_weekday, annot=True, fmt='.0f', cmap='RdYlBu_r', ax=ax,
            linewidths=0.5, cbar_kws={'label': '平均票价（元）', 'shrink': 0.8})
ax.set_title('周内效应 × 提前期热力图（验证周五高峰/周六低谷）', fontweight='bold')
ax.set_xlabel('提前天数区间'); ax.set_ylabel('出发星期')
plt.tight_layout(); plt.show()

# =====================================================
# E4: 空铁竞合分析（全修复版）
# =====================================================
# In[]
# ----- 基础数据准备（修复：航空全日期）-----
fp_hsr_valid = fp[fp['hsr_data_available'] == 1].copy()

# 航空日均价：全日期（不限制高铁有效）
air_daily_all = fp.groupby('dep_date')['price'].agg(['mean', 'std', 'count']).reset_index()
air_daily_all.columns = ['dep_date', 'air_avg', 'air_std', 'flight_count']

# 高铁最新查询日数据
hsr_df = pd.read_parquet('processed_data.parquet')[['dep_date', 'query_date', 'price_C', 'price_F', 'price_S',
                                                      'remain_C', 'remain_F', 'remain_S']].drop_duplicates()
hsr_latest_valid = hsr_df.sort_values('query_date').groupby('dep_date').last().reset_index()

# 合并：左连接，保留航空全部日期
combined_full = air_daily_all.merge(
    hsr_latest_valid[['dep_date', 'price_S', 'price_F', 'price_C', 'remain_C', 'remain_F', 'remain_S']],
    on='dep_date', how='left'
)

print(f"\n航空数据覆盖日期数：{len(air_daily_all)} 天")
print(f"高铁有效匹配日期数：{combined_full['price_F'].notna().sum()} 天")

# 日期边界
all_dates = sorted(fp['dep_date'].unique())
min_date, max_date = all_dates[0], all_dates[-1]

def merge_ranges(dates_list):
    if not dates_list: return []
    ranges = []
    start = prev = dates_list[0]
    for d in dates_list[1:]:
        if (d - prev).days == 1:
            prev = d
        else:
            ranges.append((start, prev))
            start = prev = d
    ranges.append((start, prev))
    return ranges

weekend_dates = [d for d in all_dates if pd.to_datetime(d).weekday() >= 5]
holiday_set = set()
for s, e in holiday_ranges:
    for d in pd.date_range(s, e).date:
        holiday_set.add(d)
weekend_dates = [d for d in weekend_dates if d not in holiday_set]

def draw_weekend_holiday_shading(ax, date_min, date_max):
    wk_dates = [d for d in weekend_dates if date_min <= d <= date_max]
    for start, end in merge_ranges(wk_dates):
        ax.axvspan(start, end, facecolor='#a8d8ea', alpha=0.25, zorder=1,
                   edgecolor='#5dacbd', linewidth=1.0)
    for s, e in holiday_ranges:
        start_eff = max(s, date_min)
        end_eff = min(e, date_max)
        if start_eff <= end_eff:
            ax.axvspan(start_eff, end_eff, facecolor='#ffd3b6', alpha=0.35, zorder=1,
                       edgecolor='#ff9a76', linewidth=1.0)

weekend_patch = Patch(facecolor='#a8d8ea', alpha=0.4, edgecolor='#5dacbd', linewidth=1.5, label='周末')
holiday_patch = Patch(facecolor='#ffd3b6', alpha=0.5, edgecolor='#ff9a76', linewidth=1.5, label='节假日')

# ----- 基础数据准备（修复：排除高铁票价为0的假数据）-----
fp_hsr_valid = fp[fp['hsr_data_available'] == 1].copy()

# 航空日均价：全日期
air_daily_all = fp.groupby('dep_date')['price'].agg(['mean', 'std', 'count']).reset_index()
air_daily_all.columns = ['dep_date', 'air_avg', 'air_std', 'flight_count']

# 高铁最新查询日数据（从 processed_data.parquet 重建，但过滤掉票价==0的记录）
hsr_df = pd.read_parquet('processed_data.parquet')[
    ['dep_date', 'query_date', 'price_C', 'price_F', 'price_S', 'remain_C', 'remain_F', 'remain_S']
].drop_duplicates()

# 将票价列为0的设为 NaN，后续用 notna() 自然过滤
for col in ['price_C', 'price_F', 'price_S', 'remain_C', 'remain_F', 'remain_S']:
    hsr_df.loc[hsr_df[col] == 0, col] = np.nan

# 取每个出发日期的最后一条查询记录（此时票价非NaN才算有效）
hsr_latest_valid = hsr_df.sort_values('query_date').groupby('dep_date').last().reset_index()
# 进一步剔除完全无票价的行（可选，因为后面合并时会自然剔除）
hsr_latest_valid = hsr_latest_valid[hsr_latest_valid['price_C'].notna()]

# 内连接：自动只保留高铁有真实价格的日期
combined = air_daily_all.merge(
    hsr_latest_valid[['dep_date', 'price_S', 'price_F', 'price_C', 'remain_C', 'remain_F', 'remain_S']],
    on='dep_date', how='inner'
)

# 重新计算真正的有效日期边界
all_dates = sorted(combined['dep_date'].unique())
min_date, max_date = all_dates[0], all_dates[-1]

print(f"有效空铁匹配日期数：{len(combined)} 天，范围：{min_date} ~ {max_date}")

# ----- E4-1 空铁价格时序对比（仅有效匹配日期）-----
fig, ax1 = plt.subplots(figsize=(12, 5))
ax2 = ax1.twinx()

ax1.plot(combined['dep_date'], combined['air_avg'], 'o-', color=COLORS['main'],
         linewidth=1.5, markersize=3, markerfacecolor='white', markeredgewidth=0.8,
         label='航空日均价', zorder=5)
ax1.fill_between(combined['dep_date'],
                 combined['air_avg'] - combined['air_std'],
                 combined['air_avg'] + combined['air_std'],
                 color=COLORS['main'], alpha=0.08, zorder=2)

ax2.plot(combined['dep_date'], combined['price_S'], color=COLORS['sub2'],
         marker='s', linestyle='--', linewidth=1.0, markersize=3,
         markerfacecolor='white', markeredgewidth=0.8, label='高铁二等座', zorder=5)
ax2.plot(combined['dep_date'], combined['price_F'], color=COLORS['sub3'],
         marker='^', linestyle='--', linewidth=1.0, markersize=3,
         markerfacecolor='white', markeredgewidth=0.8, label='高铁一等座', zorder=5)
ax2.plot(combined['dep_date'], combined['price_C'], color=COLORS['sub1'],
         marker='D', linestyle='-', linewidth=1.2, markersize=3,
         markerfacecolor='white', markeredgewidth=0.8, label='高铁商务座', zorder=5)

draw_weekend_holiday_shading(ax1, min_date, max_date)

lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
all_lines = lines1 + lines2 + [weekend_patch, holiday_patch]
all_labels = labels1 + labels2 + ['周末', '节假日']
ax1.legend(all_lines, all_labels, loc='upper right', fontsize=7, 
           framealpha=0.9, fancybox=False, edgecolor=COLORS['gray_mid'])

ax1.set_xlabel('出发日期', fontsize=11)
ax1.set_ylabel('航空票价（元）', color=COLORS['main'], fontsize=11)
ax2.set_ylabel('高铁票价（元）', color=COLORS['sub1'], fontsize=11)
ax1.set_title('航空与高铁各等级票价时间序列对比', fontweight='bold', pad=10)
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
fig.autofmt_xdate(rotation=45)

hsr_max_price = combined[['price_S', 'price_F', 'price_C']].max().max()
ax2.set_ylim(0, hsr_max_price * 1.15)
ax1.set_xlim(min_date, max_date)
ax1.spines['top'].set_visible(False)
ax2.spines['top'].set_visible(False)
ax1.grid(True, axis='y', alpha=0.3, linestyle='--', zorder=0)
plt.tight_layout()
plt.show()

# ----- E4-1b 高铁余票时序-----
fig, ax1 = plt.subplots(figsize=(12, 5))
ax2 = ax1.twinx()

ax1.plot(combined['dep_date'], combined['air_avg'], '-', color=COLORS['main'],
         linewidth=1.5, alpha=0.7, label='航空日均价 (参考)')

ax2.plot(combined['dep_date'], combined['remain_S'], color=COLORS['sub2'],
         marker='s', linestyle='-', linewidth=1.0, markersize=2, label='二等座余票')
ax2.plot(combined['dep_date'], combined['remain_F'], color=COLORS['sub3'],
         marker='^', linestyle='-', linewidth=1.0, markersize=2, label='一等座余票')
ax2.plot(combined['dep_date'], combined['remain_C'], color=COLORS['sub1'],
         marker='D', linestyle='-', linewidth=1.2, markersize=2, label='商务座余票')

draw_weekend_holiday_shading(ax1, min_date, max_date)


lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
all_lines = lines1 + lines2 + [weekend_patch, holiday_patch]
all_labels = labels1 + labels2 + ['周末', '节假日']
ax1.legend(all_lines, all_labels, loc='upper right', fontsize=7,
           framealpha=0.9, fancybox=False, edgecolor=COLORS['gray_mid'])

ax1.set_xlabel('出发日期', fontsize=11)
ax1.set_ylabel('航空票价（元）', color=COLORS['main'], fontsize=11)
ax2.set_ylabel('高铁余票（张）', color=COLORS['gray_dark'], fontsize=11)
ax1.set_title('高铁各等级余票时序及航空票价对比（有效匹配数据）', fontweight='bold')
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
ax1.xaxis.set_major_locator(mdates.AutoDateLocator())   # 显示完整日期
fig.autofmt_xdate(rotation=45)
ax1.set_xlim(min_date, max_date)
ax1.grid(True, axis='y', alpha=0.3, linestyle='--')
plt.tight_layout()
plt.show()

# ----- E4-2 分窗口 RPA 弹性系数-----
windows = ['0-2天', '3-7天', '8-14天']
coef_list = []
for win in windows:
    # 选取该窗口下有高铁数据的记录
    sub = fp[(fp['window_fine'] == win) & (fp['hsr_data_available'] == 1)]
    # 按出发日期聚合：航空均价 和 RPA 均值
    daily = sub.groupby('dep_date').agg(air_avg=('price', 'mean'),
                                        rpa_avg=('rpa_F', 'mean')).reset_index()
    merged_w = daily.dropna(subset=['air_avg', 'rpa_avg'])
    if len(merged_w) < 10:
        coef_list.append({'窗口': win, '回归系数': np.nan, '标准误': np.nan, 'p值': np.nan})
        continue
    X = sm.add_constant(merged_w['rpa_avg'])
    model = sm.OLS(merged_w['air_avg'], X).fit()
    coef_list.append({
        '窗口': win,
        '回归系数': model.params['rpa_avg'],
        'p值': model.pvalues['rpa_avg'],
        '标准误': model.bse['rpa_avg']
    })
coef_df = pd.DataFrame(coef_list)

# 将系数转换为“RPA每增加0.1”的影响，让数值更易读
coef_df['回归系数_scaled'] = coef_df['回归系数'] * 0.1
coef_df['标准误_scaled'] = coef_df['标准误'] * 0.1

fig, ax = plt.subplots(figsize=(5.5, 3.8))
colors_bar = COLORS['palette'][:len(windows)]
bars = ax.bar(coef_df['窗口'], coef_df['回归系数_scaled'], yerr=coef_df['标准误_scaled'],
              color=colors_bar, edgecolor='white', capsize=4)
ax.axhline(0, color=COLORS['gray_dark'], linewidth=0.8)
ax.set_ylabel('航空均价变动（元/RPA增加0.1）')
ax.set_title('空铁价格弹性系数 (基于 RPA，0-14 天细分)', fontweight='bold')
for i, row in coef_df.iterrows():
    if not np.isnan(row['p值']) and row['p值'] < 0.05:
        ax.text(i, row['回归系数_scaled'] + row['标准误_scaled'] + 0.02, '*', ha='center', fontsize=10)
despine(ax)
plt.tight_layout()
plt.show()

print("\n===== 分窗口弹性系数表 (RPA 每增加 0.1) =====")
print(coef_df[['窗口', '回归系数_scaled', '标准误_scaled', 'p值']].round(2).to_string(index=False))


# ----- 分窗口航空均价与 RPA 对比（样式与4-1a一致）-----
windows_plot = ['0-2天', '3-7天', '8-14天']
fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True)

for ax, win in zip(axes, windows_plot):
    sub = fp[(fp['window_fine'] == win) & (fp['hsr_data_available'] == 1)]
    daily = sub.groupby('dep_date').agg(
        air_avg=('price', 'mean'),
        rpa_avg=('rpa_F', 'mean')
    ).reset_index()

    ax.plot(daily['dep_date'], daily['air_avg'], 'o-',
            color=COLORS['main'], markersize=2, label='航空均价', zorder=5)

    ax2 = ax.twinx()
    if len(daily) > 0:
        ax2.plot(daily['dep_date'], daily['rpa_avg'], 's--',
                 color=COLORS['sub3'], markersize=2, label='RPA', zorder=5)

    if len(daily) > 0:
        sub_dates = sorted(daily['dep_date'].unique())
        sub_min, sub_max = sub_dates[0], sub_dates[-1]
        draw_weekend_holiday_shading(ax, sub_min, sub_max)

    ax.set_ylabel('航空 (元)')
    ax2.set_ylabel('RPA', color=COLORS['sub3'])
    ax.set_title(f'{win}', fontsize=9, fontweight='bold')
    ax.grid(True, alpha=0.3)

# 全局图例：左上，与4-1a相同样式（包含航空、RPA、节假日、周末）
lines1, labels1 = axes[0].get_legend_handles_labels()
ax2_0 = axes[0].twinx()
ax2_0.plot([], [], 's--', color=COLORS['sub3'], label='RPA')   # 制作RPA图例
lines2, labels2 = ax2_0.get_legend_handles_labels()
ax2_0.remove()
fig.legend(lines1 + lines2 + [holiday_patch, weekend_patch],
           labels1 + labels2 + ['节假日', '周末'],
           loc='upper right', fontsize=7, framealpha=0.9, fancybox=False,
           edgecolor=COLORS['gray_mid'])

# 横轴日期设置（最后一个子图）
axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
axes[-1].xaxis.set_major_locator(mdates.AutoDateLocator())
fig.autofmt_xdate(rotation=45)
fig.suptitle('分提前窗口航空均价与 RPA 对比 (0‑14 天有效数据)', fontweight='bold', y=1.01)
plt.tight_layout()
plt.show()

# ----- E4-3 新竞争特征时序图（样式统一的最终版）-----
def plot_dual_axis_v2(dep_dates, air_prices, comp_values, comp_label, comp_color, title, corr_text):
    fig, ax1 = plt.subplots(figsize=(12, 5))
    ax2 = ax1.twinx()

    # 航空日均价（COLORS['main'] 深灰蓝，与E4-1相同）
    line1, = ax1.plot(dep_dates, air_prices, 'o-', color=COLORS['main'],
                      markersize=3, linewidth=1.5, label='航空日均价', zorder=5)
    # 高铁竞争特征（comp_color）
    line2, = ax2.plot(dep_dates, comp_values, '-s', color=comp_color,
                      markersize=3, linewidth=1.5, label=comp_label, zorder=5)

    # 周末/节假日阴影
    draw_weekend_holiday_shading(ax1, dep_dates.min(), dep_dates.max())

    # 双轴颜色
    ax1.set_ylabel('航空票价（元）', color=COLORS['main'])
    ax2.set_ylabel(comp_label, color=comp_color)
    ax1.tick_params(axis='y', labelcolor=COLORS['main'])
    ax2.tick_params(axis='y', labelcolor=comp_color)

    # 日期格式（自动刻度）
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')

    # 图例：右上，无边框
    lines = [line1, line2]
    labels = [line1.get_label(), line2.get_label()]
    ax1.legend(lines, labels, loc='upper right', frameon=False, fontsize=7)

    # 标题（主标题）
    ax1.set_title(title, fontweight='bold', pad=18, fontsize=10)

    # 相关系数置于左上角（无背景框）
    ax1.text(0.02, 0.97, corr_text, transform=ax1.transAxes, fontsize=8,
             verticalalignment='top', horizontalalignment='left',
             color='black')

    despine(ax1)
    despine(ax2)
    ax1.grid(True, axis='y', alpha=0.3, linestyle='--', zorder=0)

    plt.tight_layout()
    plt.show()

# 绘制 RPA
air_daily = fp.groupby('dep_date')['price'].mean().reset_index()
air_daily.columns = ['dep_date', 'air_avg']
rpa_daily = fp[hsr_mask].groupby('dep_date')['rpa_F'].mean().reset_index()
merged = air_daily.merge(rpa_daily, on='dep_date', how='inner').dropna()
if len(merged) > 2:
    r, p = pearsonr(merged['rpa_F'], merged['air_avg'])
    plot_dual_axis_v2(
        merged['dep_date'], merged['air_avg'], merged['rpa_F'],
        '高铁-航空价格比 (RPA)', COLORS['sub3'],
        '高铁相对价格优势 (RPA) 与航空票价走势',
        f'Pearson r = {r:.3f}, p = {p:.4f}'
    )

# 绘制供给紧张度
supply_daily = fp[hsr_mask].groupby('dep_date')['supply_tension_F'].mean().reset_index()
merged = air_daily.merge(supply_daily, on='dep_date', how='inner').dropna()
if len(merged) > 2:
    r, p = pearsonr(merged['supply_tension_F'], merged['air_avg'])
    plot_dual_axis_v2(
        merged['dep_date'], merged['air_avg'], merged['supply_tension_F'],
        '高铁供给紧张度 (0-1)', COLORS['sub2'],
        '高铁供给紧张度（同提前期标准化）与航空票价走势',
        f'Pearson r = {r:.3f}, p = {p:.4f}'
    )
# ----- E4-4: 分提前期 RPA 异质性-----
print("\n" + "="*60)
print("分提前期 RPA 异质性检验...")
print("="*60)

fig, axes = plt.subplots(1, 3, figsize=(18, 5))
axes = axes.flatten()

period_results = []
period_configs = [
    ("中期 (7-30天)", (fp['days_prior'] >= 7) & (fp['days_prior'] <= 30)),
    ("临期 (3-7天)", (fp['days_prior'] >= 3) & (fp['days_prior'] < 7)),
    ("极临期 (<3天)", fp['days_prior'] < 3),
]

for idx, (period, period_mask) in enumerate(period_configs):
    mask = hsr_mask & period_mask
    sub = fp.loc[mask, ['rpa_F', 'price']].dropna()
    
    if len(sub) < 30:
        print(f"  {period}: 样本不足 ({len(sub)})，跳过")
        axes[idx].text(0.5, 0.5, '样本不足', transform=axes[idx].transAxes, 
                       ha='center', va='center', fontsize=12)
        continue
    
    r, p = pearsonr(sub['rpa_F'], sub['price'])
    slope = np.polyfit(sub['rpa_F'], sub['price'], 1)[0]
    period_results.append({'period': period, 'n': len(sub), 'r': r, 'p': p, 'slope': slope})
    
    print(f"  {period}: n={len(sub):5d} | r={r:+.3f} | p={p:.4f} | 斜率={slope:+7.1f}")

    ax = axes[idx]
    ax.scatter(sub['rpa_F'], sub['price'], alpha=0.3, s=15, c='steelblue', edgecolors='none')
    
    x_line = np.linspace(sub['rpa_F'].min(), sub['rpa_F'].max(), 100)
    z = np.polyfit(sub['rpa_F'], sub['price'], 1)
    ax.plot(x_line, np.poly1d(z)(x_line), 'r--', linewidth=2, 
            label=f'y={z[0]:.0f}x+{z[1]:.0f}')
    ax.axvline(x=1.0, color='gray', linestyle=':', alpha=0.7, label='RPA=1(价格持平)')
    
    ax.set_title(f'{period}\nr={r:.3f}, p={p:.4f}, n={len(sub)}', fontsize=11)
    ax.set_xlabel('高铁-航空价格比 (RPA)', fontsize=10)
    ax.set_ylabel('航空票价（元）', fontsize=10)
    ax.legend(fontsize=8, loc='best')

plt.suptitle('RPA 与航空票价的相关性：分提前期异质性', fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
plt.show()

# Fisher Z 检验
from scipy.stats import norm
print("\n--- 相关系数差异显著性检验（Fisher Z） ---")
results_df = pd.DataFrame(period_results)
for i in range(len(results_df)):
    for j in range(i+1, len(results_df)):
        r1, n1 = results_df.loc[i, 'r'], results_df.loc[i, 'n']
        r2, n2 = results_df.loc[j, 'r'], results_df.loc[j, 'n']
        z1 = 0.5 * np.log((1 + r1) / (1 - r1))
        z2 = 0.5 * np.log((1 + r2) / (1 - r2))
        se = np.sqrt(1/(n1-3) + 1/(n2-3))
        z_stat = (z1 - z2) / se
        p_diff = 2 * (1 - norm.cdf(abs(z_stat)))
        print(f"  {results_df.loc[i,'period']} vs {results_df.loc[j,'period']}: "
              f"Δr={r1-r2:+.3f}, Z={z_stat:+.2f}, p={p_diff:.4f}")

# ----- E4-5: RPA 阈值效应 -----
print("\n" + "="*60)
print("RPA 阈值效应检验（分段回归）...")
print("="*60)

segment_stats = fp[hsr_mask].groupby('rpa_segment')['price'].agg(['mean', 'median', 'std', 'count'])
print(segment_stats)

# 改为一致风格的箱线图
fig, ax = plt.subplots(figsize=(10, 5))
order = sorted(fp.loc[hsr_mask, 'rpa_segment'].dropna().unique())
sns.boxplot(x='rpa_segment', y='price', data=fp[hsr_mask], order=order, ax=ax,
            palette=[COLORS['main']]*len(order), width=0.5,
            boxprops=dict(alpha=0.8), 
            medianprops=dict(color=COLORS['sub1'], linewidth=1.5),
            whiskerprops=dict(color=COLORS['gray_dark'], linewidth=0.8),
            capprops=dict(color=COLORS['gray_dark'], linewidth=0.8),
            flierprops=dict(marker='o', markerfacecolor=COLORS['gray_mid'],
                           markeredgecolor='none', markersize=2, alpha=0.5))
ax.set_title('航空票价分布：按高铁-航空价格比分段', fontweight='bold', pad=10)
ax.set_xlabel('RPA 分段')
ax.set_ylabel('票价（元）')
ax.tick_params(axis='x', rotation=15)
despine(ax)
plt.tight_layout()
plt.show()

# ----- E4-6: 供给紧张度条件效应 -----
print("\n" + "="*60)
print("供给紧张度条件效应：节假日 vs 平日...")
print("="*60)

for is_hol in [0, 1]:
    label = '节假日' if is_hol else '平日'
    mask = hsr_mask & (fp['is_holiday'] == is_hol)
    sub = fp.loc[mask, ['supply_tension_F', 'price']].dropna()
    if len(sub) > 10:
        r, p = pearsonr(sub['supply_tension_F'], sub['price'])
        print(f"  {label}: r={r:+.3f}, p={p:.4f}, n={len(sub)}")

fig, ax = plt.subplots(figsize=(9, 5))
for is_hol, color, label in [(0, 'steelblue', '平日'), (1, 'coral', '节假日')]:
    mask = hsr_mask & (fp['is_holiday'] == is_hol)
    sub = fp.loc[mask]
    ax.scatter(sub['supply_tension_F'], sub['price'],
               alpha=0.4, s=15, c=color, label=label, edgecolors='none')
    if len(sub) > 30:
        valid = sub[['supply_tension_F', 'price']].dropna()
        z = np.polyfit(valid['supply_tension_F'], valid['price'], 1)
        x_line = np.linspace(valid['supply_tension_F'].min(), valid['supply_tension_F'].max(), 100)
        ax.plot(x_line, np.poly1d(z)(x_line), color=color, linewidth=2, linestyle='--')

ax.set_xlabel('高铁供给紧张度 (0-1)', fontsize=11)
ax.set_ylabel('航空票价（元）', fontsize=11)
ax.set_title('供给紧张度对航空票价的影响：节假日 vs 平日', fontsize=12)
ax.legend()
plt.tight_layout()
plt.show()

# =====================================================
# E5: 节假日 N 型效应
# =====================================================
if holiday_ranges:
    fig, ax = plt.subplots(figsize=(8, 4))
    for s, e in holiday_ranges:
        if e < min_date or s > max_date:
            continue
        window_start = max(s - timedelta(days=3), min_date)
        window_end = min(e + timedelta(days=2), max_date)
        sub = fp[(fp['dep_date'] >= window_start) & (fp['dep_date'] <= window_end)]
        if len(sub) == 0:
            continue
        daily = sub.groupby('dep_date').agg(air_avg=('price', 'mean')).reset_index()
        daily['rel_day'] = daily['dep_date'].apply(lambda d: (d - s).days + 1 if d >= s else (d - s).days)

        hsr_sub = hsr_latest_valid[(hsr_latest_valid['dep_date'] >= window_start) &
                                   (hsr_latest_valid['dep_date'] <= window_end)]
        ax.plot(daily['rel_day'], daily['air_avg'], 'o-', color=COLORS['main'],
                linewidth=1.5, markersize=4, label=f'航空均价 ({s}~{e})')
        if len(hsr_sub) > 0:
            hsr_sub = hsr_sub[['dep_date', 'price_C']].copy()
            hsr_sub['rel_day'] = hsr_sub['dep_date'].apply(lambda d: (d - s).days + 1 if d >= s else (d - s).days)
            ax.plot(hsr_sub['rel_day'], hsr_sub['price_C'], 's--', color=COLORS['sub1'],
                    linewidth=1.2, markersize=3, label=f'高铁商务座 ({s}~{e})')
    ax.axvline(0, color=COLORS['gray_dark'], linestyle='--', alpha=0.5, linewidth=0.8)
    if holiday_ranges:
        first_s, first_e = holiday_ranges[0]
        ax.axvspan(1, (first_e - first_s).days + 1, facecolor='#ffd3b6', alpha=0.2, zorder=0)
    ax.set_xlabel('相对节假日位置（天）：负数=节前，0=首日，正数=假期中/后')
    ax.set_ylabel('票价（元）')
    ax.set_title('节假日 N 型效应：航空 vs 高铁商务座', fontweight='bold')
    ax.legend(loc='upper right', fontsize=6.5, frameon=True, fancybox=False, edgecolor=COLORS['gray_mid'])
    despine(ax)
    plt.tight_layout()
    plt.show()

# =====================================================
# E6: 展会效应
# =====================================================
grouped = fp.groupby(['day_type', 'is_expo_day'])['price'].mean().reset_index()
pivot_expo = grouped.pivot(index='day_type', columns='is_expo_day', values='price')
pivot_expo.columns = ['非展会日', '展会日']

fig, ax = plt.subplots(figsize=(4.5, 3.5))
x = np.arange(len(pivot_expo)); width = 0.35
bars1 = ax.bar(x - width/2, pivot_expo['非展会日'], width, label='非展会日', color=COLORS['main'], edgecolor='white')
bars2 = ax.bar(x + width/2, pivot_expo['展会日'], width, label='展会日', color=COLORS['sub1'], edgecolor='white')
for bars in [bars1, bars2]:
    for bar in bars:
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width()/2., h + 5, f'{h:.0f}', ha='center', va='bottom', fontsize=7)
ax.set_xticks(x); ax.set_xticklabels(pivot_expo.index)
ax.set_ylabel('平均票价（元）'); ax.set_title('展会效应：展会日 vs 非展会日', fontweight='bold')
ax.legend(frameon=True, fancybox=False, edgecolor=COLORS['gray_mid']); despine(ax)
plt.tight_layout(); plt.show()

print("\n===== 展会溢价统计检验 =====")
for day_type in ['工作日', '非工作日']:
    sub = fp[fp['day_type'] == day_type]
    expo_p = sub[sub['is_expo_day'] == 1]['price']
    non_p = sub[sub['is_expo_day'] == 0]['price']
    if len(expo_p) >= 2 and len(non_p) >= 2:
        t, p = ttest_ind(expo_p, non_p)
        print(f"{day_type}: 展会日={expo_p.mean():.0f}元, 非展会日={non_p.mean():.0f}元, "
              f"溢价={expo_p.mean()-non_p.mean():+.0f}元, p={p:.4f}")

print("\n✅ EDA 全部分析完成！")
# %%
