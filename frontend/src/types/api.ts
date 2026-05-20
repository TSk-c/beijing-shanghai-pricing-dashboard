/** GET /api/price/distribution */
export interface PriceDistributionResponse {
  bins: { start: number; end: number; density: number }[];
  median: number;
  mean: number;
  skewness: number;
  kurtosis: number;
}

/** GET /api/rail-air/rpa-trend */
export interface RpaTrendResponse {
  dates: string[];
  airPrices: number[];
  rpaValues: number[];
  hsrSecond: number[];
  hsrFirst: number[];
  hsrBusiness: number[];
  weekends: number[];
  holidays?: { start: number; end: number };
  pearson_r?: number | null;
  pearson_p?: number | null;
}

export interface ModelComparisonLayerMetrics {
  mae: (number | null)[];
  mape: (number | null)[];
  rmse: (number | null)[];
}

/** GET /api/model/comparison */
export interface ModelComparisonResponse {
  models: string[];
  layers: string[];
  overall: ModelComparisonLayerMetrics;
  layered: Record<string, ModelComparisonLayerMetrics>;
}

export interface PredictDriver {
  feature: string;
  shap_value: number;
  feature_value?: number;
  direction: string;
  category?: string;
}

export interface ShapWaterfallItem {
  feature: string;
  shap_value: number;
  category: string;
}

export interface CategoryTopFeature {
  feature: string;
  shap_value: number;
}

export interface CategorySummary {
  total_abs_contribution: number;
  net_contribution: number;
  top_features: CategoryTopFeature[];
}

export interface ShapDetail {
  all_features: PredictDriver[];
  waterfall: ShapWaterfallItem[];
  category_summary: Record<string, CategorySummary>;
}

export interface CompetitiveStatus {
  rpa_level: string;
  supply_status: string;
  recommendation: string;
}

/** POST /api/model/predict-flight */
export interface PredictResponse {
  flight_no?: string;
  dep_date?: string;
  days_prior?: number;
  predicted_price: number;
  base_value?: number;
  confidence_interval: [number, number];
  prediction_interval_95?: [number, number];
  key_drivers: PredictDriver[];
  shap_detail?: ShapDetail;
  competitive_status?: CompetitiveStatus;
}

/** GET /api/data-panorama */
export interface DataPanoramaResponse {
  data_quality: {
    total_records: number;
    missing_count: number;
    missing_rate: number;
    anomaly_count: number;
    low_coverage_dates: string[];
    daily_records: { date: string; count: number }[];
  };
  collection_coverage: {
    air: {
      query_date_range: { start: string; end: string };
      dep_date_range: { start: string; end: string };
      query_days: number;
      dep_days: number;
      unique_flights: number;
      daily_flights: { date: string; count: number }[];
    };
    hsr: {
      query_date_range: { start: string; end: string };
      dep_date_range: { start: string; end: string };
      query_days: number;
      total_records: number;
    };
    expo: {
      total: number;
      date_range: { start: string; end: string };
    };
  };
  sample_distribution: {
    airlines: { name: string; count: number }[];
    dep_airports: { name: string; count: number }[];
    arr_airports: { name: string; count: number }[];
    price_stats: {
      min: number;
      max: number;
      mean: number;
      median: number;
      std: number;
    };
    weekday_count: number;
    weekend_count: number;
    holiday_count: number;
    normal_count: number;
  };
}

/** GET /api/eda/charts */
export interface EdaChartsResponse {
  quantile_curve: {
    days: number[];
    p10: number[];
    p25: number[];
    p50: number[];
    p75: number[];
    p90: number[];
  };
  typical_dates: {
    label: string;
    days: number[];
    prices: number[];
  }[];
  box_plot: {
    bins: string[];
    box_data: Record<string, number[]>;
    stats: {
      bin: string;
      mean: number;
      median: number;
      q1: number;
      q3: number;
      count: number;
    }[];
    overall_median: number;
  };
  airline_curves: Record<string, {
    days: number[];
    prices: number[];
  }>;
  airlines: string[];
  heatmap: {
    dow_names: string[];
    columns: string[];
    matrix: (number | null)[][];
  };
  remain_trend: {
    dates: string[];
    air_avg: number[];
    remain_C: number[];
    remain_F: number[];
    remain_S: number[];
    weekends: number[];
    holidays?: { start: number; end: number };
  };
  supply_trend: {
    dates: string[];
    air_avg: number[];
    supply_avg: number[];
    pearson_r: number | null;
    pearson_p: number | null;
    weekends: number[];
    holidays?: { start: number; end: number };
  };
  rpa_heterogeneity: {
    period: string;
    n: number;
    r: number | null;
    p: number | null;
    slope: number | null;
    scatter_rpa: number[];
    scatter_price: number[];
  }[];
  rpa_segment: {
    segments: string[];
    stats: {
      segment: string;
      mean: number;
      median: number;
      std: number;
      count: number;
    }[];
    box_data: Record<string, number[]>;
  };
  supply_effect: {
    scatter: {
      label: string;
      r: number;
      p: number;
      tension: number[];
      price: number[];
    }[];
  };
  n_shape: {
    start: string;
    end: string;
    air_rel_days: number[];
    air_prices: number[];
    hsr_rel_days?: number[];
    hsr_prices?: (number | null)[];
  }[];
  holiday_ranges: {
    start: string;
    end: string;
  }[];
  expo_effect: {
    day_types: string[];
    non_expo: number[];
    expo: number[];
  };
  expo_tests: {
    day_type: string;
    expo_mean: number;
    non_expo_mean: number;
    premium: number;
    t_stat: number;
    p_value: number;
  }[];
  rpa_elasticity: {
    window: string;
    coef: number | null;
    coef_scaled: number | null;
    std_err_scaled: number | null;
    p_value: number | null;
  }[];
  windowed_rpa: {
    window: string;
    dates: string[];
    air_avg: number[];
    rpa_avg: number[];
    weekends: number[];
    holidays?: { start: number; end: number };
  }[];
}

/** GET /api/model/performance */
export interface ModelPerformanceResponse {
  overall: {
    n: number;
    rmse: number;
    mae: number;
    mape: number;
    r2: number;
    adj_r2: number;
    ev: number;
    me: number;
    max_err: number;
    med_ae: number;
  };
  window_metrics: {
    window: string;
    n: number;
    rmse: number;
    mae: number;
    mape: number;
    r2: number;
    adj_r2: number;
    ev: number;
    me: number;
    max_err: number;
    med_ae: number;
  }[];
  scenario_metrics: {
    scenario: string;
    n: number;
    rmse: number;
    mae: number;
    mape: number;
    r2: number;
    adj_r2: number;
    ev: number;
    me: number;
    max_err: number;
    med_ae: number;
  }[];
  shap_global: {
    feature: string;
    importance: number;
    scatter: { value: number; shap: number }[];
  }[];
  hsr_contribution: {
    overall_pct: number;
    available_pct: number;
    feature_contributions: {
      feature: string;
      importance: number;
      is_hsr: boolean;
    }[];
    period_contributions: {
      period: string;
      hsr_pct: number;
      rpa_pct: number;
      n: number;
    }[];
  };
  sensitivity: Record<string, {
    value: number;
    rmse: number;
    mae: number;
    mape: number;
    r2: number;
  }[]>;
  n_features: number;
}
