import type { EChartsOption } from 'echarts';
import {
  CHART_LINE_1,
  CHART_LINE_2,
  CHART_LINE_3,
  CHART_LINE_4,
  SHAP_HIGH,
  SHAP_LOW,
  WARNING,
  TEXT_PRIMARY,
  TEXT_MUTED,
} from '../constants/colors';

const LEGEND_TOP_RIGHT = { top: 5, right: 10 };

export function buildWindowRadarOption(
  windows: { window: string; rmse: number; mae: number; mape: number; r2: number; ev: number }[],
): EChartsOption {
  const indicator = [
    { name: 'RMSE', max: Math.max(...windows.map((w) => w.rmse)) * 1.1 },
    { name: 'MAE', max: Math.max(...windows.map((w) => w.mae)) * 1.1 },
    { name: 'MAPE', max: Math.max(...windows.map((w) => w.mape)) * 1.1 },
    { name: 'R²', max: 1 },
    { name: '解释方差', max: 1 },
  ];
  const palette = [CHART_LINE_1, CHART_LINE_2, CHART_LINE_3, CHART_LINE_4];
  return {
    tooltip: {},
    legend: { ...LEGEND_TOP_RIGHT },
    radar: { indicator, shape: 'polygon', radius: '65%' },
    series: [{
      type: 'radar',
      data: windows.map((w, i) => ({
        name: w.window,
        value: [w.rmse, w.mae, w.mape, w.r2, w.ev],
        lineStyle: { color: palette[i % palette.length] },
        areaStyle: { color: palette[i % palette.length], opacity: 0.15 },
        itemStyle: { color: palette[i % palette.length] },
      })),
    }],
  };
}

export function buildShapSwarmOption(
  shapData: { feature: string; importance: number; scatter: { value: number; shap: number }[] }[],
): EChartsOption {
  const features = shapData.map((s) => s.feature);
  const allShap = shapData.flatMap((s) => s.scatter.map((p) => Math.abs(p.shap)));
  const maxShap = Math.max(...allShap, 0.01);
  const seriesData: number[][] = [];
  for (let fi = 0; fi < shapData.length; fi++) {
    const pts = shapData[fi].scatter;
    const vals = pts.map((p) => p.value);
    const minV = Math.min(...vals);
    const maxV = Math.max(...vals);
    const range = maxV - minV || 1;
    for (const pt of pts) {
      const norm = (pt.value - minV) / range;
      seriesData.push([pt.shap, fi, norm]);
    }
  }

  return {
    tooltip: {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      formatter(params: any) {
        const p = Array.isArray(params) ? params[0] : params;
        const fi = p.value[1] as number;
        return `${features[fi]}<br/>SHAP: ${p.value[0].toFixed(3)}<br/>特征值: ${p.value[2].toFixed(3)}`;
      },
    },
    grid: { top: 20, right: 60, bottom: 30, left: 130 },
    xAxis: {
      type: 'value',
      name: 'SHAP 值',
      nameLocation: 'end',
      nameGap: 5,
      min: -maxShap * 1.1,
      max: maxShap * 1.1,
    },
    yAxis: {
      type: 'category',
      data: features,
      inverse: true,
      axisLabel: { fontSize: 11 },
    },
    visualMap: {
      show: true,
      orient: 'horizontal',
      min: 0,
      max: 1,
      dimension: 2,
      bottom: 0,
      left: 'center',
      text: ['高', '低'],
      inRange: { color: [SHAP_LOW, SHAP_HIGH] },
      itemWidth: 12,
      itemHeight: 80,
    },
    series: [{
      type: 'scatter',
      data: seriesData,
      symbolSize: 3,
      emphasis: { itemStyle: { borderColor: '#333', borderWidth: 1 } },
    }],
  };
}

export function buildHsrContributionPieOption(
  featureContributions: { feature: string; importance: number; is_hsr: boolean }[],
): EChartsOption {
  const hsrTotal = featureContributions.filter((f) => f.is_hsr).reduce((s, f) => s + f.importance, 0);
  const otherTotal = featureContributions.filter((f) => !f.is_hsr).reduce((s, f) => s + f.importance, 0);
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {d}%' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie',
      radius: ['40%', '65%'],
      center: ['50%', '45%'],
      label: { show: true, formatter: '{b}\n{d}%', fontSize: 11 },
      data: [
        { name: '高铁竞争特征', value: round(hsrTotal, 4), itemStyle: { color: CHART_LINE_3 } },
        { name: '其他特征', value: round(otherTotal, 4), itemStyle: { color: CHART_LINE_1 } },
      ],
    }],
  };
}

export function buildHsrContributionWaterfallOption(
  featureContributions: { feature: string; importance: number; is_hsr: boolean }[],
): EChartsOption {
  const sorted = [...featureContributions].sort((a, b) => b.importance - a.importance);
  const names = sorted.map((f) => f.feature);
  const values = sorted.map((f) => f.importance);
  const colors = sorted.map((f) => (f.is_hsr ? CHART_LINE_3 : CHART_LINE_1));
  return {
    tooltip: { trigger: 'axis' },
    grid: { top: 20, right: 100, bottom: 30, left: 130 },
    xAxis: { type: 'value', name: '平均 |SHAP|', nameLocation: 'end', nameGap: 5 },
    yAxis: { type: 'category', data: names, inverse: true, axisLabel: { fontSize: 10 } },
    series: [{
      type: 'bar',
      data: values.map((v, i) => ({ value: v, itemStyle: { color: colors[i] } })),
      barWidth: '60%',
      label: { show: true, position: 'right', formatter: '{c}', fontSize: 9 },
    }],
  };
}

export function buildPeriodContributionOption(
  periodData: { period: string; hsr_pct: number; rpa_pct: number; n: number }[],
): EChartsOption {
  return {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255,255,255,0.96)',
      borderColor: '#E0E0E0',
      textStyle: { color: TEXT_PRIMARY, fontSize: 12 },
    },
    legend: { data: ['高铁总贡献', 'RPA单独贡献'], ...LEGEND_TOP_RIGHT, textStyle: { color: TEXT_PRIMARY } },
    grid: { top: 40, right: 100, bottom: 30, left: 130 },
    xAxis: {
      type: 'value',
      name: '贡献占比 (%)',
      nameLocation: 'end',
      nameGap: 5,
      max: 100,
      axisLabel: { color: TEXT_MUTED },
      splitLine: { lineStyle: { type: 'dashed', color: '#E5E7EB' } },
    },
    yAxis: {
      type: 'category',
      data: periodData.map((p) => p.period),
      inverse: true,
      axisLabel: { color: TEXT_PRIMARY, fontSize: 12 },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: [
      {
        name: '高铁总贡献',
        type: 'bar',
        data: periodData.map((p) => p.hsr_pct),
        itemStyle: { color: CHART_LINE_3, borderRadius: [0, 4, 4, 0] },
        barWidth: '30%',
        label: { show: true, position: 'right', formatter: '{c}%', fontSize: 10, color: TEXT_MUTED },
      },
      {
        name: 'RPA单独贡献',
        type: 'bar',
        data: periodData.map((p) => p.rpa_pct),
        itemStyle: { color: CHART_LINE_1, borderRadius: [0, 4, 4, 0] },
        barWidth: '30%',
        label: { show: true, position: 'right', formatter: '{c}%', fontSize: 10, color: TEXT_MUTED },
      },
    ],
  };
}

export function buildSensitivityLineOption(
  paramName: string,
  data: { value: number; rmse: number; mae: number; mape: number; r2: number }[],
): EChartsOption {
  const values = data.map((d) => String(d.value));
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['RMSE', 'MAE', 'MAPE'], ...LEGEND_TOP_RIGHT },
    grid: { top: 40, right: 40, bottom: 120, left: 80 },
    dataZoom: [
      { type: 'inside', xAxisIndex: 0, filterMode: 'none' },
      { type: 'slider', xAxisIndex: 0, height: 22, bottom: 40, filterMode: 'none' },
    ],
    xAxis: { type: 'category', data: values, name: paramName, nameLocation: 'end', nameGap: 5, axisLabel: { rotate: 30 } },
    yAxis: [
      { type: 'value', name: '误差', position: 'left', nameLocation: 'middle', nameGap: 55, scale: true },
    ],
    series: [
      { name: 'RMSE', type: 'line', data: data.map((d) => d.rmse), yAxisIndex: 0, lineStyle: { width: 2 }, symbolSize: 6, itemStyle: { color: CHART_LINE_1 } },
      { name: 'MAE', type: 'line', data: data.map((d) => d.mae), yAxisIndex: 0, lineStyle: { width: 2 }, symbolSize: 6, itemStyle: { color: CHART_LINE_2 } },
      { name: 'MAPE', type: 'line', data: data.map((d) => d.mape), yAxisIndex: 0, lineStyle: { width: 2 }, symbolSize: 6, itemStyle: { color: WARNING } },
    ],
  };
}

function round(v: number, d: number): number {
  return Math.round(v * 10 ** d) / 10 ** d;
}
