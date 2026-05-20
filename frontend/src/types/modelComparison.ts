export interface ModelComparisonRow {
  key: string;
  layer: string;
  layerRowSpan: number;
  metric: string;
  values: (number | null)[];
}
