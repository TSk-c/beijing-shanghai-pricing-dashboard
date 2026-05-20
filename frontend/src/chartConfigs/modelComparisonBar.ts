import type { EChartsOption } from 'echarts';
import { BG_PRIMARY, PRIMARY, SHAP_NEUTRAL, TEXT_PRIMARY } from '../constants/colors';

const XGBOOST = 'XGBoost';

/** 非 XGBoost 模型柱状颜色（灰色系） */
const BAR_GREY = SHAP_NEUTRAL;

/**
 * 横向柱状图：每个模型一个 series，便于图例点击显隐。
 * XGBoost 使用主色高亮，其余为灰色系。
 */
export function modelComparisonBarConfig(
  models: string[],
  values: number[],
  metricName: string,
): EChartsOption {
  const series = models.map((model, idx) => ({
    name: model,
    type: 'bar' as const,
    data: models.map((_, j) => (j === idx ? values[idx] : ('-' as const))),
    emphasis: { focus: 'series' as const },
    itemStyle: {
      color: model === XGBOOST ? PRIMARY : BAR_GREY,
    },
  }));

  return {
    title: {
      text: metricName,
      left: 'center',
      top: 4,
      textStyle: { fontSize: 14, color: TEXT_PRIMARY },
    },
    tooltip: {
      trigger: 'item',
      formatter: (params: unknown) => {
        const p = params as { seriesName?: string; value?: number | string };
        const v = p.value;
        if (v === '-' || v == null || Number.isNaN(Number(v))) {
          return '';
        }
        return `${p.seriesName ?? ''}<br/>${metricName}：${Number(v).toFixed(2)}`;
      },
    },
    legend: {
      type: 'scroll',
      bottom: 0,
      selectedMode: true,
      textStyle: { color: TEXT_PRIMARY },
    },
    grid: { top: 40, right: 24, bottom: 56, left: 112 },
    xAxis: {
      type: 'value',
      name: metricName,
      splitLine: { show: true, lineStyle: { type: 'dashed' } },
      nameTextStyle: { color: TEXT_PRIMARY },
    },
    yAxis: {
      type: 'category',
      data: models,
      inverse: true,
      axisLabel: { color: TEXT_PRIMARY },
    },
    series,
    backgroundColor: BG_PRIMARY,
  };
}
