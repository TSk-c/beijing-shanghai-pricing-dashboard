/** 票价分布 mock 结构 */
export interface PriceBin {
  start: number;
  end: number;
  density: number;
}

export interface PriceDistributionInput {
  bins: PriceBin[];
  median: number;
  mean: number;
  /** 分布偏度（页面统计卡展示） */
  skewness: number;
  /** 分布峰度（页面统计卡展示） */
  kurtosis: number;
}
