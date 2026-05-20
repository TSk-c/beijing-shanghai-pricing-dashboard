/** 双轴时序图输入（与 mockRpaTrend 等结构对齐） */
export interface DualAxisTimeSeriesInput {
  dates: string[];
  airPrices: number[];
  rpaValues: number[];
  /** 周末在 dates 中的下标 */
  weekends?: number[];
  /** 节假日闭区间 [start,end] 下标 */
  holidays?: { start: number; end: number };
  /** Pearson 相关系数 */
  pearsonR?: number | null;
  pearsonP?: number | null;
}

/** 空铁价格对比时序图输入（E4-1 风格：航空左轴 + 高铁三档右轴） */
export interface AirHsrPriceComparisonInput {
  dates: string[];
  airPrices: number[];
  hsrSecond: number[];
  hsrFirst: number[];
  hsrBusiness: number[];
  weekends?: number[];
  holidays?: { start: number; end: number };
}

/** 单轴面积时序输入 */
export interface ShadingTimeSeriesInput {
  dates: string[];
  values: number[];
  weekends?: number[];
  holidays?: { start: number; end: number };
  /** 系列名称 */
  seriesName?: string;
  /** Y 轴名称 */
  yAxisName?: string;
}
