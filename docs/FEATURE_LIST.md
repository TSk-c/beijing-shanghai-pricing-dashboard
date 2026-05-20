# 建模特征清单 (41维)

## 概述

特征矩阵文件: feature_matrix_final_v5.parquet
目标变量文件: target_final_v5.parquet (price)

---

## 一、时间结构特征 (6维)

| 特征名         | 类型  | 构造方式                           | 取值范围 | 说明                              |
| :--------------- | :------ | :----------------------------------- | :--------- | :---------------------------------- |
| days_prior     | int   | dep_date - query_date              | 0 ~ 89   | 提前天数                          |
| days_prior_sq  | float | days_prior ** 2                    | 0 ~ 7921 | 提前天数平方（非线性）            |
| dep_dow        | int   | pd.to_datetime(dep_date).weekday() | 0~6      | 出发星期（0=周一）                |
| dep_time_hour  | float | HH + MM/60                         | 0 ~ 24   | 出发时刻（连续）                  |
| dep_period_enc | int   | 时段编码函数                       | 0~5      | 早高峰/上午/下午/晚高峰/夜间/红眼 |
| is_weekend     | int   | (dep_dow>=5) & (is_holiday==0)     | 0/1      | 周末哑变量（节假日除外）          |

**时段编码规则**:

- 0: 07:00-09:00 (早高峰)
- 1: 09:00-12:00 (上午)
- 2: 12:00-17:00 (下午)
- 3: 17:00-20:00 (晚高峰)
- 4: 20:00-23:00 (夜间)
- 5: 其他 (红眼航班)

---

## 二、节假日生命周期特征 (7维)

| 特征名                  | 类型 | 构造方式         | 取值  | 说明             |
| :------------------------ | :----- | :----------------- | :------ | :----------------- |
| is_holiday              | int  | 原始字段         | 0/1   | 是否节假日       |
| holiday_day_num         | int  | 节假日第几天     | 1~N   | 假期内位置       |
| is_holiday_mid          | int  | 中段标记         | 0/1   | 第2天至倒数第2天 |
| is_holiday_last_2d      | int  | 末期标记         | 0/1   | 假期最后2天      |
| is_pre_holiday_peak     | int  | 节前1天          | 0/1   | 出行最高峰       |
| is_pre_holiday_buildup  | int  | 节前2-3天        | 0/1   | 需求蓄力期       |
| is_post_holiday_dip     | int  | 节后1天          | 0/1   | 需求断崖         |
| days_to_nearest_holiday | int  | 距最近节假日天数 | 0~999 | 连续度量邻近效应 |

**节假日区间**（2026年）:

- 五一假期: 2026-05-01 ~ 2026-05-05

---

## 三、航班属性特征 (4维)

| 特征名          | 类型  | 构造方式       | 说明                      |
| :---------------- | :------ | :--------------- | :-------------------------- |
| airline_enc     | int   | Label Encoding | 航空公司编码              |
| dep_airport_enc | int   | Label Encoding | 起飞机场编码（大兴/首都） |
| arr_airport_enc | int   | Label Encoding | 到达机场编码（虹桥/浦东） |
| duration_hours  | float | duration / 60  | 飞行时长（小时）          |

---

## 四、高铁基础特征 (8维)

| 特征名             | 类型  | 构造方式     | 缺失处理               |
| :------------------- | :------ | :------------- | :----------------------- |
| hsr_data_available | int   | 标记         | 0（>14天或日期边界外） |
| price_C            | float | 商务座最低价 | 中位数填充（无效样本） |
| price_F            | float | 一等座最低价 | 中位数填充             |
| price_S            | float | 二等座最低价 | 中位数填充             |
| remain_C           | float | 商务座总余票 | 中位数填充             |
| remain_F           | float | 一等座总余票 | 中位数填充             |
| remain_S           | float | 二等座总余票 | 中位数填充             |
| hsr_avg_duration_h | float | 平均历时     | 中位数填充             |
| train_count        | float | 车次数       | 中位数填充             |

**高铁有效条件**: days_prior <= 14 AND query_date在高铁数据范围内

---

## 五、核心竞争特征 (3维) ⭐

| 特征名           | 类型  | 公式                                    | 经济学含义                       |
| :----------------- | :------ | :---------------------------------------- | :--------------------------------- |
| rpa_F            | float | price_F / price                         | 高铁-航空价格比（一等座）        |
| price_diff_F     | float | price_F - price                         | 高铁-航空价格差（一等座）        |
| supply_tension_F | float | 1 - rank_pct(remain_F \| days_prior) | 高铁供给紧张度（同提前期标准化） |

**RPA解读**:

- RPA < 1: 高铁比航空便宜（价格优势）
- RPA = 1: 价格持平
- RPA > 1: 高铁比航空贵

**供给紧张度解读**:

- 0: 余票充足（同提前期前100%）
- 1: 余票极度紧张（同提前期后0%）

---

## 六、交互特征 (7维)

| 特征名                        | 公式                                       | 捕捉效应               |
| :------------------------------ | :------------------------------------------- | :----------------------- |
| rpa_F_x_days_prior            | rpa_F * days_prior                         | 价格竞争×提前期衰减   |
| supply_tension_F_x_is_holiday | supply_tension_F * is_holiday              | 供给溢出×节假日放大   |
| supply_tension_F_x_is_weekend | supply_tension_F * is_weekend              | 供给溢出×周末效应     |
| price_diff_F_x_days_prior     | price_diff_F * days_prior                  | 价格差×时间异质性     |
| rpa_F_x_is_weekend            | rpa_F * is_weekend                         | 价格竞争×周末休闲需求 |
| rpa_F_high                    | (rpa_F > 1.2).astype(int)                  | 高铁显著贵阈值         |
| rpa_F_low                     | (rpa_F < 0.8).astype(int)                  | 高铁显著便宜阈值       |
| supply_tension_high           | (supply_tension_F > 0.8分位数).astype(int) | 高紧张度标记           |

---

## 七、高铁内部结构特征 (2维)

| 特征名           | 公式                           | 说明               |
| :----------------- | :------------------------------- | :------------------- |
| hsr_F_S_spread   | price_F - price_S              | 一等座与二等座价差 |
| hsr_total_remain | remain_C + remain_F + remain_S | 全席别总余票       |

---

## 八、展会事件特征 (2维)

| 特征名         | 构造方式                                      | 说明                     |
| :--------------- | :---------------------------------------------- | :------------------------- |
| expo_max_scale | max(scale_index) for dep_date in [start, end] | 当日最大展会规模（万人） |
| is_expo_day    | 1 if dep_date in any expo range else 0        | 是否展会日               |

---

## 九、EDA用衍生字段（不入模，仅分析）

| 字段名          | 说明                                                    |
| :---------------- | :-------------------------------------------------------- |
| window          | 粗粒度窗口: 远期(≥15天)/中期(3-14天)/临期(0-2天)       |
| window_fine     | 细粒度窗口: 0-2天/3-7天/8-14天                          |
| prior_bin       | 分箱: 当天/1-2天/3-6天/7-13天/14-20天/21-30天/30天+     |
| prior_bin_heat  | 热力图分箱: 0-2天/3-6天/7-13天/14-20天/21-30天/30天+    |
| day_type        | 工作日/非工作日                                         |
| rpa_segment     | 分段: 高铁显著便宜/略便宜/价格持平/略贵/显著贵          |
| scenario_simple | 场景: 普通工作日/周末/节假日/节前高峰/节前积蓄/节后回落 |

---

## 特征重要性排序（基于SHAP全局分析）

| 排名 | 特征                    |   重要性   |
| :----: | :------------------------ | :----------: |
|  1  | days_prior              | ★★★★★ |
|  2  | dep_dow                 | ★★★★★ |
|  3  | dep_time_hour           | ★★★★☆ |
|  4  | days_to_nearest_holiday | ★★★★☆ |
|  5  | airline_enc             | ★★★★☆ |
|  6  | price_diff_F            | ★★★★☆ |
|  7  | dep_airport_enc         | ★★★☆☆ |
|  8  | days_prior_sq           | ★★★☆☆ |
|  9  | rpa_F                   | ★★★☆☆ |
|  10  | duration_hours          | ★★★☆☆ |
| ... | ...                     |    ...    |