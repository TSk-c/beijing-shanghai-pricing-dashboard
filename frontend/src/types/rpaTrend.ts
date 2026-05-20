/** RPA 时序全量序列（mockRpaTrend） */
export interface RpaTrendChartInput {
  dates: string[];
  airPrices: number[];
  rpaValues: number[];
  hsrSecond: number[];
  hsrFirst: number[];
  hsrBusiness: number[];
  weekends?: number[];
  holidays?: { start: number; end: number };
  pearsonR?: number | null;
  pearsonP?: number | null;
}
