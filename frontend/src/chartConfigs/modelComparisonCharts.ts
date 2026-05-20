import type { EChartsOption } from 'echarts';
import type { ModelComparisonLayerMetrics } from '../types/api';
import {
  BG_PRIMARY,
  PRIMARY,
  TEXT_PRIMARY,
  SHAP_NEUTRAL,
  TEXT_SECONDARY,
} from '../constants/colors';

const XGBOOST = 'XGBoost';

export function buildModelComparisonGroupedBar(
  allLayers: string[],
  models: string[],
  dataMap: Record<string, ModelComparisonLayerMetrics>,
  metric: 'mae' | 'mape' | 'rmse',
): EChartsOption {
  const metricLabel = metric === 'mape' ? 'MAPE (%)' : metric.toUpperCase();

  const bestModelByLayer: string[] = [];
  for (const layer of allLayers) {
    const layerData = dataMap[layer];
    if (!layerData) {
      bestModelByLayer.push('');
      continue;
    }
    const layerValues = layerData[metric];
    let bestIdx = -1;
    let bestVal = Infinity;
    for (let i = 0; i < layerValues.length; i++) {
      const v = layerValues[i];
      if (v != null && v < bestVal) {
        bestVal = v;
        bestIdx = i;
      }
    }
    bestModelByLayer.push(bestIdx >= 0 ? models[bestIdx] : '');
  }

  const MODEL_COLORS: Record<string, string> = {
    XGBoost: PRIMARY,
    LightGBM: '#2196F3',
    GradientBoosting: '#4CAF50',
    '\u968F\u673A\u68EE\u6797': '#FF9800',
    ElasticNet: '#9C27B0',
    Lasso: '#E91E63',
    Ridge: '#607D8B',
    LSTM: '#F44336',
  };

  const series = models.map((model, modelIdx) => ({
    name: model,
    type: 'bar' as const,
    barMaxWidth: 36,
    barGap: '10%' as const,
    itemStyle: {
      color: MODEL_COLORS[model] ?? SHAP_NEUTRAL,
    },
    data: allLayers.map((layer, layerIdx) => {
      const layerData = dataMap[layer];
      if (!layerData) return null;
      const val = layerData[metric][modelIdx] ?? null;
      const isBest = model === bestModelByLayer[layerIdx];
      return {
        value: val,
        itemStyle: {
          color: MODEL_COLORS[model] ?? SHAP_NEUTRAL,
          opacity: isBest ? 1 : 0.3,
          borderRadius: [3, 3, 0, 0],
        },
        label: {
          show: isBest,
          position: 'top' as const,
          formatter: () => model,
          fontSize: 10,
          color: MODEL_COLORS[model] ?? PRIMARY,
          fontWeight: 'bold',
          distance: 4,
        },
      };
    }),
    emphasis: { focus: 'series' as const },
  }));

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: 'rgba(255,255,255,0.96)',
      borderColor: '#E0E0E0',
      textStyle: { color: TEXT_PRIMARY, fontSize: 12 },
    },
    legend: {
      type: 'scroll',
      bottom: 0,
      textStyle: { color: TEXT_PRIMARY, fontSize: 11 },
    },
    grid: { top: 40, right: 24, bottom: 56, left: 56 },
    xAxis: {
      type: 'category',
      data: allLayers,
      axisLabel: { color: TEXT_PRIMARY, fontSize: 11, interval: 0 },
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#E0E0E0' } },
    },
    yAxis: {
      type: 'value',
      name: metricLabel,
      splitLine: { lineStyle: { type: 'dashed', color: '#E8E8E8' } },
      nameTextStyle: { color: TEXT_SECONDARY, fontSize: 11 },
      axisLabel: { color: TEXT_SECONDARY, fontSize: 11 },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series,
    backgroundColor: BG_PRIMARY,
  };
}

export function buildModelComparisonOverallBar(
  models: string[],
  values: (number | null)[],
  metricName: string,
): EChartsOption {
  const sorted = models
    .map((m, i) => ({ model: m, value: values[i] }))
    .filter((x) => x.value != null)
    .sort((a, b) => (a.value ?? 0) - (b.value ?? 0));

  const bestVal = sorted.length > 0 ? sorted[0].value : undefined;
  const titleText = metricName.includes('MAPE') ? 'MAPE (%)' : metricName.toUpperCase();

  return {
    title: {
      text: titleText,
      left: 'center',
      top: 0,
      textStyle: { fontSize: 13, fontWeight: 600, color: TEXT_PRIMARY },
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
    },
    grid: { top: 32, right: 96, bottom: 20, left: 96 },
    xAxis: {
      type: 'value',
      splitLine: { lineStyle: { type: 'dashed', color: '#E8E8E8' } },
      axisLabel: { color: TEXT_SECONDARY, fontSize: 11 },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'category',
      data: sorted.map((x) => x.model),
      inverse: true,
      axisLabel: { color: TEXT_PRIMARY, fontSize: 11 },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: [
      {
        type: 'bar',
        barMaxWidth: 18,
        data: sorted.map((x) => ({
          value: x.value,
          itemStyle: {
            color: x.value === bestVal ? PRIMARY : SHAP_NEUTRAL,
            borderRadius: [0, 3, 3, 0],
          },
        })),
        label: {
          show: true,
          position: 'right',
          formatter: (p: unknown) => {
            const v = (p as { value?: number }).value;
            return metricName.includes('MAPE') ? `${v?.toFixed(2)}%` : v?.toFixed(2) ?? '';
          },
          fontSize: 11,
          color: TEXT_SECONDARY,
        },
      },
    ],
    backgroundColor: BG_PRIMARY,
  };
}
