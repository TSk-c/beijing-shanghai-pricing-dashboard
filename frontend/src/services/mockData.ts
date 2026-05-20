// Mock数据 - 用于前端开发阶段，格式严格符合API规范

export const mockOverview = {
  total_records: 213456,
  hsr_coverage: 0.24,
  date_range: { start: "2026-04-08", end: "2026-07-16" },
  best_model_mape: 6.46
};

export const mockPriceDistribution = {
  bins: Array.from({ length: 80 }, (_, i) => ({
    start: 400 + i * 25,
    end: 425 + i * 25,
    density: Math.exp(-Math.pow((500 + i * 25 - 920) / 300, 2) / 2) / (300 * Math.sqrt(2 * Math.PI)) + Math.random() * 0.0001
  })),
  median: 850,
  mean: 920,
  skewness: 1.45,
  kurtosis: 2.83
};

export const mockBookingCurve = {
  days_prior: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 20, 25, 30, 40, 50, 60, 89],
  prices: [1200, 1150, 1100, 1050, 1000, 950, 920, 880, 860, 850, 840, 835, 830, 825, 820, 810, 800, 790, 780, 770, 760, 750, 740],
  date_type: "普通周三"
};

export const mockRpaTrend = {
  dates: Array.from({ length: 41 }, (_, i) => {
    const d = new Date('2026-04-08');
    d.setDate(d.getDate() + i);
    return d.toISOString().split('T')[0];
  }),
  airPrices: Array.from({ length: 41 }, (_, i) => 800 + Math.sin(i / 5) * 200 + Math.random() * 100),
  rpaValues: Array.from({ length: 41 }, (_, i) => 1.0 + Math.sin(i / 7) * 0.3 + Math.random() * 0.1),
  hsrSecond: Array.from({ length: 41 }, () => 553),
  hsrFirst: Array.from({ length: 41 }, () => 933),
  hsrBusiness: Array.from({ length: 41 }, () => 1748 + Math.random() * 100),
  weekends: [5, 6, 12, 13, 19, 20, 26, 27, 33, 34, 40], // 周末索引
  holidays: { start: 23, end: 27 }, // 五一假期索引
  pearson_r: -0.452,
  pearson_p: 0.003,
};

export const mockElasticity = {
  windows: ["0-2天", "3-7天", "8-14天"],
  coefficients: [-106.76, -83.75, -24.86],
  std_errors: [5.06, 5.83, 8.23],
  p_values: [0.0001, 0.0001, 0.01]
};

export const mockModelComparison = {
  models: ["Ridge", "Lasso", "ElasticNet", "RandomForest", "GradientBoosting", "LightGBM", "XGBoost", "LSTM"],
  layers: ["0-3天(临期)", "4-7天(中期)", "8-14天(远期)", "15天+(超远期)"],
  overall: {
    mae: [125.82, 122.46, 117.16, 85.39, 78.32, 63.33, 57.21, 489.07],
    mape: [17.11, 16.70, 16.66, 11.51, 10.20, 8.18, 6.46, 54.58],
    rmse: [176.29, 171.94, 166.83, 132.75, 120.25, 117.56, 123.25, 560.36],
  },
  layered: {
    "0-3天(临期)": {
      mae: [66.53, 67.95, 65.85, 30.02, 38.08, 19.90, 18.01, null],
      mape: [7.45, 7.69, 7.52, 3.52, 4.53, 2.23, 1.97, null],
      rmse: [78.68, 78.59, 88.48, 40.05, 45.62, 25.90, 24.36, null],
    },
    "4-7天(中期)": {
      mae: [62.80, 57.33, 52.78, 20.11, 23.62, 28.02, 24.93, 454.39],
      mape: [9.67, 9.13, 8.48, 3.35, 3.51, 4.17, 3.73, 52.42],
      rmse: [71.69, 65.01, 65.52, 27.09, 30.51, 35.45, 33.62, 524.58],
    },
    "8-14天(远期)": {
      mae: [76.33, 69.09, 69.37, 58.18, 62.14, 74.82, 90.20, 470.69],
      mape: [12.62, 11.37, 11.65, 10.04, 10.35, 12.42, 15.07, 53.89],
      rmse: [178.07, 152.72, 184.07, 232.22, 208.68, 243.97, 298.06, 535.05],
    },
    "15天+(超远期)": {
      mae: [137.06, 133.92, 127.89, 94.44, 84.95, 66.47, 57.94, 491.03],
      mape: [18.45, 18.09, 18.07, 12.51, 10.85, 8.31, 7.22, 54.67],
      rmse: [183.70, 181.02, 172.05, 126.36, 114.50, 104.36, 98.92, 562.82],
    },
  },
};

export const mockShapGlobal = {
  features: ["days_prior", "dep_dow", "dep_time_hour", "days_to_nearest_holiday", "airline_enc", "price_diff_F", "dep_airport_enc", "days_prior_sq", "rpa_F", "duration_hours"],
  shapValues: Array.from({ length: 10 }, (_, featIdx) => 
    Array.from({ length: 100 }, () => ({
      shap: (Math.random() - 0.5) * (10 - featIdx) * 10,
      value: Math.random()
    }))
  )
};

export const mockWindowPerformance = {
  windows: ["0-2天", "3-7天", "8-14天", "15天+"],
  rmse: [24.94, 23.51, 189.80, 86.91],
  mae: [17.59, 16.64, 47.95, 49.35],
  mape: [1.66, 2.20, 7.97, 6.07],
  r2: [1.00, 0.99, -0.53, 0.83]
};

export const mockPredictResult = {
  predicted_price: 892.5,
  base_value: 800,
  confidence_interval: [796.8, 988.2],
  prediction_interval_95: [700.0, 1085.0],
  key_drivers: [
    { feature: "days_prior", shap_value: -45.2, feature_value: 7, direction: "negative", category: "时间因素" },
    { feature: "rpa_F", shap_value: -28.5, feature_value: 0.95, direction: "negative", category: "高铁竞争" },
    { feature: "dep_dow", shap_value: 22.0, feature_value: 3, direction: "positive", category: "时间因素" },
    { feature: "expo_max_scale", shap_value: 15.0, feature_value: 2, direction: "positive", category: "展会冲击" },
    { feature: "is_pre_holiday_peak", shap_value: 12.0, feature_value: 0, direction: "positive", category: "节假日效应" },
  ],
  shap_detail: {
    all_features: [
      { feature: "days_prior", shap_value: -45.2, feature_value: 7, direction: "negative", category: "时间因素" },
      { feature: "rpa_F", shap_value: -28.5, feature_value: 0.95, direction: "negative", category: "高铁竞争" },
      { feature: "dep_dow", shap_value: 22.0, feature_value: 3, direction: "positive", category: "时间因素" },
      { feature: "expo_max_scale", shap_value: 15.0, feature_value: 2, direction: "positive", category: "展会冲击" },
      { feature: "is_pre_holiday_peak", shap_value: 12.0, feature_value: 0, direction: "positive", category: "节假日效应" },
    ],
    waterfall: [
      { feature: "days_prior", shap_value: -45.2, category: "时间因素" },
      { feature: "rpa_F", shap_value: -28.5, category: "高铁竞争" },
      { feature: "is_pre_holiday_peak", shap_value: 12.0, category: "节假日效应" },
      { feature: "expo_max_scale", shap_value: 15.0, category: "展会冲击" },
      { feature: "dep_dow", shap_value: 22.0, category: "时间因素" },
    ],
    category_summary: {
      "时间因素": { total_abs_contribution: 67.2, net_contribution: -23.2, top_features: [{ feature: "days_prior", shap_value: -45.2 }, { feature: "dep_dow", shap_value: 22.0 }] },
      "高铁竞争": { total_abs_contribution: 28.5, net_contribution: -28.5, top_features: [{ feature: "rpa_F", shap_value: -28.5 }] },
      "展会冲击": { total_abs_contribution: 15.0, net_contribution: 15.0, top_features: [{ feature: "expo_max_scale", shap_value: 15.0 }] },
      "节假日效应": { total_abs_contribution: 12.0, net_contribution: 12.0, top_features: [{ feature: "is_pre_holiday_peak", shap_value: 12.0 }] },
    },
  },
  competitive_status: {
    rpa_level: "高铁略贵",
    supply_status: "宽松",
    recommendation: "维持当前定价"
  }
};

export const mockHeatmap = {
  heatmapData: [
    // [xIndex, yIndex, value]  x:提前期(0-5), y:星期(0-6)
    [0, 0, 680], [1, 0, 720], [2, 0, 750], [3, 0, 780], [4, 0, 800], [5, 0, 820],
    [0, 1, 650], [1, 1, 700], [2, 1, 730], [3, 1, 760], [4, 1, 790], [5, 1, 810],
    [0, 2, 640], [1, 2, 690], [2, 2, 720], [3, 2, 750], [4, 2, 780], [5, 2, 800],
    [0, 3, 660], [1, 3, 710], [2, 3, 740], [3, 3, 770], [4, 3, 800], [5, 3, 820],
    [0, 4, 850], [1, 4, 900], [2, 4, 950], [3, 4, 1000], [4, 4, 1050], [5, 4, 1100],
    [0, 5, 700], [1, 5, 720], [2, 5, 740], [3, 5, 760], [4, 5, 780], [5, 5, 800],
    [0, 6, 750], [1, 6, 780], [2, 6, 820], [3, 6, 860], [4, 6, 900], [5, 6, 950]
  ]
};

export const mockAirlineCompare = {
  airlines: ["中国国航", "东方航空", "南方航空", "春秋航空", "吉祥航空"],
  curves: Array.from({ length: 5 }, (_, airlineIdx) => ({
    name: ["中国国航", "东方航空", "南方航空", "春秋航空", "吉祥航空"][airlineIdx],
    data: Array.from({ length: 30 }, (_, day) => 600 + airlineIdx * 100 + Math.sin(day / 5) * 150 + day * 5)
  }))
};