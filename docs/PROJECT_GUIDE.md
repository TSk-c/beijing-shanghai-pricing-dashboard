# 项目开发指南

## 系统定位
京沪空铁竞争定价可视化分析系统，展示空铁竞争定价的全链路分析，从数据预处理到模型洞察。

## 核心用户
航空收益管理分析师、定价策略师、数据科学家。

## 页面清单（29个）

### 模块1：数据全景（1页）
- /data-overview：数据质量监控、采集覆盖度

### 模块2：票价分析（5页）
- /price-analysis/distribution：票价分布直方图+KDE
- /price-analysis/booking-curve：提前期预订曲线（可选日期类型）
- /price-analysis/quantile：分位数扩散图
- /price-analysis/boxplot：关键区间箱线图
- /price-analysis/airline-compare：航司预订曲线对比
- /price-analysis/weekday-heatmap：周内效应×提前期热力图

### 模块3：空铁竞合（9页）
- /rail-air-competition/rpa-trend：RPA时序走势（双轴）
- /rail-air-competition/supply：高铁余票时序
- /rail-air-competition/elasticity：弹性系数分析
- /rail-air-competition/window-comparison：分窗口RPA对比（3子图）
- /rail-air-competition/correlation：RPA与航空票价走势
- /rail-air-competition/supply-tension：供给紧张度走势
- /rail-air-competition/heterogeneity：分提前期异质性（3散点图）
- /rail-air-competition/threshold：RPA阈值效应（分段箱线图）
- /rail-air-competition/conditional：供给紧张度条件效应
- /rail-air-competition/holiday-n：节假日N型效应
- /rail-air-competition/expo：展会效应

### 模块4：模型洞察（8页）
- /model-insights/comparison：模型对比（2×2布局）
- /model-insights/shap-global：SHAP蜂群图
- /model-insights/shap-rpa：RPA边际影响（SHAP依赖图）
- /model-insights/shap-supply：供给紧张度SHAP
- /model-insights/shap-subset：SHAP特征重要性子集
- /model-insights/window-performance：分窗口性能（表格+雷达图）
- /model-insights/scenario-performance：分场景性能
- /model-insights/hyperparameter：超参数敏感性

### 模块5：实时定价（3页）
- /pricing-system/single-flight：单航班定价预测
- /pricing-system/batch-predict：批量预测
- /pricing-system/strategy：策略建议

## 数据流
前端 → FastAPI → 读取Parquet/SQLite → 预聚合 → JSON返回 → ECharts渲染

## 关键约束
- 21万条记录必须后端预聚合，前端不接原始数据
- SHAP值后端预计算缓存
- 日期统一使用YYYY-MM-DD字符串
- 所有金额保留1位小数，百分比保留2位小数