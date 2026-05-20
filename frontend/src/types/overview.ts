/** GET /api/overview 响应（snake_case，与后端一致） */
export interface OverviewResponse {
  total_records: number;
  hsr_coverage: number;
  date_range: { start: string; end: string };
  best_model_mape: number;
}
