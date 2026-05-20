# 京沪空铁定价可视化分析系统

基于 XGBoost 的北京-上海航线动态定价预测与可视化分析平台，集成 SHAP 归因解读、空铁竞争分析、多模型对比等功能。

## 系统架构

```
┌─────────────────────────────────────────────────┐
│                  展示层 (React + ECharts)         │
│  票价分析 │ 空铁竞争 │ 模型洞察 │ 定价规则解读     │
└──────────────────────┬──────────────────────────┘
                       │ RESTful API (JSON)
┌──────────────────────┴──────────────────────────┐
│                  服务层 (FastAPI)                  │
│  数据查询 │ XGBoost预测 │ SHAP解释 │ 统计分析      │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────┐
│                  数据层                           │
│  SQLite │ Parquet │ CSV                          │
└─────────────────────────────────────────────────┘
```

## 功能模块

### 票价分析
- **票价分布**：各航司票价箱线图、分舱位分布对比
- **提前天数分析**：不同提前购票天数与价格的关系
- **航司与热力图**：航司-星期-提前天数三维热力图

### 空铁竞争
- **RPA综合分析**：高铁-航空价格比(RPA)趋势、弹性分析
- **空铁价格与余票**：航空与高铁票价、余票双轴对比
- **节假日与展会**：节假日/展会期间票价异常检测

### 模型洞察
- **模型对比**：8种回归模型分提前期窗口性能对比
- **XGBoost性能**：整体/分窗口/分情景性能、SHAP全局解释、参数敏感性

### 定价规则解读
- 单航班价格预测（多提前天数）
- SHAP特征归因瀑布图
- 因素类别贡献对比（时间/节假日/展会/航班属性/高铁竞争）
- 最优购买时机建议与置信区间

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + TypeScript + Ant Design 5 + ECharts 5 |
| 后端 | FastAPI + Pandas + XGBoost + SHAP |
| 数据 | SQLite + Parquet + CSV |
| 构建 | Vite |
| 状态管理 | Zustand |

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+

### 后端启动

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 前端启动

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173

## 项目结构

```
beijing-shanghai-pricing-dashboard/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── routers/             # API 路由
│   │   └── services/
│   │       ├── data_loader.py   # 数据加载与缓存
│   │       └── model_service.py # XGBoost预测与SHAP计算
│   ├── data/                    # 数据文件（需自行准备）
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/               # 页面组件
│   │   ├── components/          # 通用组件
│   │   ├── chartConfigs/        # ECharts 配置
│   │   ├── services/            # API 服务
│   │   ├── constants/           # 颜色等常量
│   │   ├── types/               # TypeScript 类型
│   │   └── store/               # Zustand 状态
│   └── package.json
├── model.py                     # 模型训练脚本
├── feature_engineering.py       # 特征工程
└── eda_visualization.py         # EDA 可视化
```

## 数据说明

项目使用北京-上海航线的航空票价与高铁票价数据，包含以下特征维度：

- **时间特征**：出发日期、星期、提前天数、时段
- **航班属性**：航司、舱位价格/余票
- **高铁竞争**：RPA（高铁-航空价格比）、高铁余票、供给紧张度
- **节假日/展会**：节假日前中后期标记、展会影响
- **交叉特征**：RPA×提前天数、供给紧张度×节假日等


