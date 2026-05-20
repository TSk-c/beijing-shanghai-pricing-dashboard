# 数据库结构文档 (air_hsr_pricing.db)

## 概述

SQLite数据库，包含4张表：航班基础信息、航班价格记录、高铁日聚合数据、展会信息。

---

## 表1: flights（航班基础信息）

| 列名        | 类型  | 说明             | 示例      |
| :------------ | :------ | :----------------- | :---------- |
| flight_no   | TEXT  | 主键             | CA1234    |
| airline     | TEXT  | 航空公司         | 中国国航  |
| dep_airport | TEXT  | 起飞机场         | 大兴/首都 |
| arr_airport | TEXT  | 到达机场         | 虹桥/浦东 |
| dep_time    | TEXT  | 起飞时间 HH:MM   | 08:30     |
| arr_time    | TEXT  | 到达时间 HH:MM   | 10:45     |
| duration    | FLOAT | 飞行时长（分钟） | 135.0     |

---

## 表2: flight_prices（航班价格记录）

| 列名        | 类型   | 说明             | 示例       |
| :------------ | :------- | :----------------- | :----------- |
| flight_no   | TEXT   | 航班号           | CA1234     |
| airline     | TEXT   | 航空公司         | 中国国航   |
| dep_airport | TEXT   | 起飞机场         | 大兴       |
| arr_airport | TEXT   | 到达机场         | 虹桥       |
| dep_time    | TEXT   | 起飞时间         | 08:30      |
| arr_time    | TEXT   | 到达时间         | 10:45      |
| duration    | FLOAT  | 飞行时长（分钟） | 135.0      |
| query_date  | DATE   | 查询日期         | 2026-04-08 |
| dep_date    | DATE   | 出发日期         | 2026-04-15 |
| days_prior  | BIGINT | 提前天数         | 7          |
| price       | BIGINT | 经济舱票价（元） | 850        |
| discount    | FLOAT  | 折扣系数 0-1     | 0.35       |
| cabin_class | TEXT   | 舱位             | 经济舱     |
| is_weekend  | BIGINT | 是否周末 0/1     | 0          |
| is_holiday  | BIGINT | 是否节假日 0/1   | 0          |

**记录数**: ~213,000条
**时间范围**: query_date 2026-04-08 至 2026-04-26
**dep_date范围**: 2026-04-08 至 2026-07-16（未来89天）

---

## 表3: hsr_prices（高铁日聚合数据）

| 列名               | 类型   | 说明                         | 示例       |
| :------------------- | :------- | :----------------------------- | :----------- |
| query_date         | DATE   | 查询日期                     | 2026-04-08 |
| dep_date           | DATE   | 出发日期                     | 2026-04-15 |
| price_C            | FLOAT  | 商务座最低价                 | 1748.0     |
| price_F            | FLOAT  | 一等座最低价                 | 933.0      |
| price_S            | FLOAT  | 二等座最低价                 | 553.0      |
| remain_C           | BIGINT | 商务座总余票                 | 45         |
| remain_F           | BIGINT | 一等座总余票                 | 120        |
| remain_S           | BIGINT | 二等座总余票                 | 856        |
| train_count        | BIGINT | 当日G字头车次数              | 43         |
| hsr_avg_duration_h | FLOAT  | 高铁平均历时（小时，十进制） | 4.9        |
| days_prior         | BIGINT | 提前天数                     | 7          |
| is_weekend         | BIGINT | 是否周末 0/1                 | 0          |
| is_holiday         | BIGINT | 是否节假日 0/1               | 0          |

**记录数**: ~50,000条（聚合后）
**覆盖**: 仅提前期≤14天有数据
**车次筛选**: 仅保留G字头列车

---

## 表4: expos（展会信息）

| 列名        | 类型  | 说明             | 示例               |
| :------------ | :------ | :----------------- | :------------------- |
| name        | TEXT  | 展会名称         | 中国国际工业博览会 |
| city        | TEXT  | 城市             | 上海               |
| start_date  | DATE  | 开始日期         | 2026-05-12         |
| end_date    | DATE  | 结束日期         | 2026-05-16         |
| scale_index | FLOAT | 观众人数（万人） | 28.5               |
| venue       | TEXT  | 举办展馆         | 国家会展中心       |

**记录数**: ~30条
**覆盖**: 北京、上海 2026年4-9月大型展会

---

## 关键关联关系

flight\_prices.query\_date + flight\_prices.dep\_date → hsr\_prices.query\_date + hsr\_prices.dep\_date (LEFT JOIN)

flight\_prices.dep\_date → expos.start\_date \~ expos.end\_date (范围匹配)


---

## 数据清洗规则（预处理时应用）

1. 删除 price <= 0 的记录
2. 删除 discount > 1.0 的记录
3. 删除矛盾记录: (discount<0.1 & price>1000) 或 (price<200 & discount>0.5)
4. 分航空公司1%和99%分位数盖帽，再全局0.5%和99.5%分位数盖帽
5. 按 flight_no, query_date, dep_date, dep_time 去重
6. 高铁数据: 票价=0的设为NaN，取每个dep_date的最后一条查询记录