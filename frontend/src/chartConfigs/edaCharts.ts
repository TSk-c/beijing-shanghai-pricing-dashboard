import type { EChartsOption } from 'echarts';
import {
  CHART_LINE_1,
  CHART_LINE_2,
  CHART_LINE_3,
  CHART_LINE_4,
  CHART_LINE_5,
  HEATMAP_MAX,
  HEATMAP_MID,
  HEATMAP_MIN,
  HOLIDAY_SHADE,
  WARNING,
  WEEKEND_SHADE,
} from '../constants/colors';

const PALETTE = [CHART_LINE_1, CHART_LINE_4, CHART_LINE_3, CHART_LINE_2, CHART_LINE_5, WARNING];

type MarkAreaPair = [
  { name: string; xAxis: string; itemStyle?: { color: string } },
  { xAxis: string },
];

function groupConsecutive(sorted: number[]): [number, number][] {
  if (sorted.length === 0) return [];
  const ranges: [number, number][] = [];
  let lo = sorted[0];
  let hi = sorted[0];
  for (let i = 1; i < sorted.length; i++) {
    if (sorted[i] === hi + 1) {
      hi = sorted[i];
    } else {
      ranges.push([lo, hi]);
      lo = hi = sorted[i];
    }
  }
  ranges.push([lo, hi]);
  return ranges;
}

function buildMarkAreaPairs(
  dates: string[],
  weekends: number[] | undefined,
  holidays: { start: number; end: number } | undefined,
): MarkAreaPair[] {
  const data: MarkAreaPair[] = [];
  if (weekends && weekends.length > 0) {
    const uniq = [...new Set(weekends)].sort((a, b) => a - b);
    for (const [lo, hi] of groupConsecutive(uniq)) {
      if (dates[lo] && dates[hi]) {
        data.push([
          { name: '周末', xAxis: dates[lo], itemStyle: { color: WEEKEND_SHADE } },
          { xAxis: dates[hi] },
        ]);
      }
    }
  }
  if (holidays && dates[holidays.start] && dates[holidays.end]) {
    data.push([
      { name: '节假日', xAxis: dates[holidays.start], itemStyle: { color: HOLIDAY_SHADE } },
      { xAxis: dates[holidays.end] },
    ]);
  }
  return data;
}

const TIME_SERIES_DATAZOOM: EChartsOption['dataZoom'] = [
  { type: 'inside', xAxisIndex: 0, filterMode: 'none' },
  { type: 'slider', xAxisIndex: 0, height: 22, bottom: 16, filterMode: 'none' },
];

const LEGEND_TOP_RIGHT = { top: 0, right: 10, backgroundColor: 'rgba(255,255,255,0.9)' };

export function buildQuantileCurveOption(
  days: number[],
  p10: number[],
  p25: number[],
  p50: number[],
  p75: number[],
  p90: number[],
): EChartsOption {
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['P10', 'P25', '中位数', 'P75', 'P90'], ...LEGEND_TOP_RIGHT },
    grid: { top: 40, right: 30, bottom: 80, left: 80 },
    dataZoom: TIME_SERIES_DATAZOOM,
    xAxis: { type: 'category', data: days, name: '提前天数', nameLocation: 'middle', nameGap: 30 },
    yAxis: { type: 'value', name: '票价（元）', nameLocation: 'middle', nameGap: 65 },
    series: [
      { name: 'P10', type: 'line', data: p10, lineStyle: { width: 1, opacity: 0.5 }, symbol: 'none', itemStyle: { color: CHART_LINE_3 } },
      { name: 'P25', type: 'line', data: p25, lineStyle: { width: 1.2, opacity: 0.7 }, symbol: 'none', itemStyle: { color: CHART_LINE_2 } },
      { name: '中位数', type: 'line', data: p50, lineStyle: { width: 2.5 }, symbol: 'none', itemStyle: { color: CHART_LINE_1 } },
      { name: 'P75', type: 'line', data: p75, lineStyle: { width: 1.2, opacity: 0.7 }, symbol: 'none', itemStyle: { color: CHART_LINE_2 } },
      { name: 'P90', type: 'line', data: p90, lineStyle: { width: 1, opacity: 0.5 }, symbol: 'none', itemStyle: { color: CHART_LINE_3 } },
    ],
  };
}

export function buildTypicalDatesOption(
  curves: { label: string; days: number[]; prices: number[] }[],
): EChartsOption {
  const allDays = [...new Set(curves.flatMap((c) => c.days))].sort((a, b) => a - b);
  return {
    tooltip: { trigger: 'axis' },
    legend: { ...LEGEND_TOP_RIGHT },
    grid: { top: 40, right: 30, bottom: 80, left: 80 },
    dataZoom: TIME_SERIES_DATAZOOM,
    xAxis: { type: 'category', data: allDays, name: '提前天数', nameLocation: 'middle', nameGap: 30 },
    yAxis: { type: 'value', name: '平均票价（元）', nameLocation: 'middle', nameGap: 65 },
    series: curves.map((c, i) => {
      const dataMap = new Map(c.days.map((d, j) => [d, c.prices[j]]));
      return {
        name: c.label,
        type: 'line',
        data: allDays.map((d) => dataMap.get(d) ?? null),
        lineStyle: { width: 1.5 },
        connectNulls: true,
        symbolSize: 4,
        itemStyle: { color: PALETTE[i % PALETTE.length] },
      };
    }),
  };
}

export function buildBoxPlotOption(
  bins: string[],
  boxData: Record<string, number[]>,
  stats: { bin: string; mean: number; median: number; q1: number; q3: number; count: number }[],
  overallMedian: number,
): EChartsOption {
  void overallMedian;
  const seriesData: number[][] = [];
  const outlierData: number[][] = [];
  const xData: string[] = [];

  for (const b of bins) {
    const values = (boxData[b] ?? []).slice().sort((a, b2) => a - b2);
    if (values.length < 5) continue;
    const q1 = stats.find((s) => s.bin === b)?.q1 ?? 0;
    const q3val = stats.find((s) => s.bin === b)?.q3 ?? 0;
    const iqr = q3val - q1;
    const lower = q1 - 1.5 * iqr;
    const upper = q3val + 1.5 * iqr;
    const whiskerLow = Math.max(lower, values[0]);
    const whiskerHigh = Math.min(upper, values[values.length - 1]);
    const med = stats.find((s) => s.bin === b)?.median ?? 0;
    seriesData.push([whiskerLow, q1, med, q3val, whiskerHigh]);
    values.forEach((v) => {
      if (v < lower || v > upper) outlierData.push([xData.length, v]);
    });
    xData.push(b);
  }

  return {
    tooltip: { trigger: 'item' },
    grid: { top: 20, right: 30, bottom: 60, left: 80 },
    xAxis: { type: 'category', data: xData, name: '提前天数区间', nameLocation: 'middle', nameGap: 40 },
    yAxis: { type: 'value', name: '票价（元）', nameLocation: 'middle', nameGap: 65 },
    series: [
      {
        name: '票价分布',
        type: 'boxplot',
        data: seriesData,
        itemStyle: { color: 'rgba(44,62,80,0.6)', borderColor: CHART_LINE_1 },
      },
      {
        name: '异常值',
        type: 'scatter',
        large: true,
        data: outlierData,
        symbolSize: 3,
        itemStyle: { color: '#95A5A6', opacity: 0.5 },
      },
    ],
  };
}

export function buildAirlineCurvesOption(
  airlines: string[],
  curves: Record<string, { days: number[]; prices: number[] }>,
): EChartsOption {
  return {
    tooltip: { trigger: 'axis' },
    legend: { type: 'scroll', ...LEGEND_TOP_RIGHT },
    grid: { top: 40, right: 30, bottom: 80, left: 80 },
    dataZoom: TIME_SERIES_DATAZOOM,
    xAxis: { type: 'category', name: '提前天数', nameLocation: 'middle', nameGap: 30 },
    yAxis: { type: 'value', name: '经济舱票价（元）', nameLocation: 'middle', nameGap: 65 },
    series: airlines.map((al, i) => ({
      name: al,
      type: 'line',
      data: curves[al].days.map((d, j) => [d, curves[al].prices[j]]),
      lineStyle: { width: 1.3 },
      symbolSize: 3,
      itemStyle: { color: PALETTE[i % PALETTE.length] },
    })),
  };
}

export function buildHeatmapOption(
  dowNames: string[],
  columns: string[],
  matrix: (number | null)[][],
): EChartsOption {
  const seriesData: [number, number, number][] = [];
  const flatValues: number[] = [];
  for (let y = 0; y < matrix.length; y++) {
    for (let x = 0; x < matrix[y].length; x++) {
      const val = matrix[y][x];
      if (val != null) {
        seriesData.push([x, y, val]);
        flatValues.push(val);
      }
    }
  }
  return {
    tooltip: {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      formatter(params: any) {
        const p = params as { data: number[] };
        if (!p.data || p.data.length < 3) return '';
        return `${dowNames[p.data[1]]} / ${columns[p.data[0]]}：${p.data[2]}元`;
      },
    },
    grid: { top: 10, right: 100, bottom: 60, left: 80 },
    xAxis: {
      type: 'category',
      data: columns,
      name: '提前天数区间',
      nameLocation: 'middle',
      nameGap: 40,
      splitArea: { show: true },
    },
    yAxis: {
      type: 'category',
      data: dowNames,
      name: '出发星期',
      nameLocation: 'middle',
      nameGap: 55,
    },
    visualMap: {
      min: flatValues.length > 0 ? Math.min(...flatValues) : 0,
      max: flatValues.length > 0 ? Math.max(...flatValues) : 100,
      calculable: true,
      orient: 'vertical',
      right: 0,
      top: 'center',
      inRange: { color: [HEATMAP_MIN, HEATMAP_MID, HEATMAP_MAX] },
    },
    series: [{
      type: 'heatmap',
      data: seriesData,
      label: { show: true, fontSize: 10 },
      emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.3)' } },
    }],
  };
}

export function buildRemainTrendOption(
  dates: string[],
  airAvg: number[],
  remainC: number[],
  remainF: number[],
  remainS: number[],
  weekends?: number[],
  holidays?: { start: number; end: number },
): EChartsOption {
  const markAreaPairs = buildMarkAreaPairs(dates, weekends, holidays);
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: { data: ['航空日均价', '商务座余票', '一等座余票', '二等座余票'], ...LEGEND_TOP_RIGHT },
    grid: { top: 50, right: 80, bottom: 80, left: 80 },
    dataZoom: TIME_SERIES_DATAZOOM,
    xAxis: { type: 'category', data: dates, axisLabel: { formatter: (v: string) => v.slice(5) } },
    yAxis: [
      { type: 'value', name: '航空票价（元）', position: 'left', nameLocation: 'middle', nameGap: 65, scale: true },
      { type: 'value', name: '余票数量', position: 'right', nameLocation: 'middle', nameGap: 55 },
    ],
    series: [
      {
        name: '航空日均价',
        type: 'line',
        data: airAvg,
        yAxisIndex: 0,
        lineStyle: { width: 1.5 },
        symbol: 'none',
        itemStyle: { color: CHART_LINE_1 },
        markArea: markAreaPairs.length > 0 ? { silent: true, data: markAreaPairs } : undefined,
      },
      { name: '商务座余票', type: 'line', data: remainC, yAxisIndex: 1, lineStyle: { width: 1.2 }, symbol: 'diamond', symbolSize: 4, itemStyle: { color: CHART_LINE_4 } },
      { name: '一等座余票', type: 'line', data: remainF, yAxisIndex: 1, lineStyle: { width: 1.2 }, symbol: 'triangle', symbolSize: 4, itemStyle: { color: CHART_LINE_3 } },
      { name: '二等座余票', type: 'line', data: remainS, yAxisIndex: 1, lineStyle: { width: 1.2 }, symbol: 'square', symbolSize: 4, itemStyle: { color: CHART_LINE_2 } },
    ],
  };
}

export function buildSupplyTrendOption(
  dates: string[],
  airAvg: number[],
  supplyAvg: number[],
  pearsonR: number | null,
  pearsonP: number | null,
  weekends?: number[],
  holidays?: { start: number; end: number },
): EChartsOption {
  const subText = pearsonR != null ? `Pearson r = ${pearsonR.toFixed(3)}, p = ${pearsonP?.toFixed(4)}` : '';
  const markAreaPairs = buildMarkAreaPairs(dates, weekends, holidays);
  return {
    title: { text: '高铁供给紧张度与航空票价走势', subtext: subText, left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: { data: ['航空日均价', '供给紧张度'], top: 40, right: 10, backgroundColor: 'rgba(255,255,255,0.9)' },
    grid: { top: 90, right: 80, bottom: 80, left: 80 },
    dataZoom: TIME_SERIES_DATAZOOM,
    xAxis: { type: 'category', data: dates, axisLabel: { formatter: (v: string) => v.slice(5) } },
    yAxis: [
      { type: 'value', name: '航空票价（元）', position: 'left', nameLocation: 'middle', nameGap: 65, scale: true },
      { type: 'value', name: '供给紧张度 (0-1)', position: 'right', min: 0, max: 1, nameLocation: 'middle', nameGap: 65 },
    ],
    series: [
      {
        name: '航空日均价',
        type: 'line',
        data: airAvg,
        yAxisIndex: 0,
        lineStyle: { width: 1.5 },
        symbol: 'none',
        itemStyle: { color: CHART_LINE_1 },
        markArea: markAreaPairs.length > 0 ? { silent: true, data: markAreaPairs } : undefined,
      },
      { name: '供给紧张度', type: 'line', data: supplyAvg, yAxisIndex: 1, lineStyle: { width: 1.5, type: 'dashed' }, symbol: 'square', symbolSize: 4, itemStyle: { color: CHART_LINE_2 } },
    ],
  };
}

export function buildRpaHeteroOption(
  period: string,
  scatterRpa: number[],
  scatterPrice: number[],
  r: number | null,
  p: number | null,
  slope: number | null,
): EChartsOption {
  const subText = r != null ? `r=${r.toFixed(3)}, p=${p?.toFixed(4)}, 斜率=${slope?.toFixed(1)}` : '';
  const scatterData = scatterRpa.map((v, i) => [v, scatterPrice[i]]);
  const lineData: number[][] = [];
  if (slope != null && scatterRpa.length > 0) {
    const minX = Math.min(...scatterRpa);
    const maxX = Math.max(...scatterRpa);
    const intercept = scatterPrice.reduce((a, b) => a + b, 0) / scatterPrice.length - slope * (scatterRpa.reduce((a, b) => a + b, 0) / scatterRpa.length);
    lineData.push([minX, slope * minX + intercept]);
    lineData.push([maxX, slope * maxX + intercept]);
  }
  return {
    title: { text: period, subtext: subText, left: 'center', textStyle: { fontSize: 13 } },
    tooltip: { trigger: 'item' },
    grid: { top: 60, right: 20, bottom: 50, left: 80 },
    xAxis: { type: 'value', name: 'RPA', nameLocation: 'middle', nameGap: 35, splitLine: { show: true, lineStyle: { type: 'dashed', opacity: 0.3 } } },
    yAxis: { type: 'value', name: '航空票价（元）', nameLocation: 'middle', nameGap: 65 },
    series: [
      {
        type: 'scatter',
        large: true,
        data: scatterData,
        symbolSize: 5,
        itemStyle: { color: 'steelblue', opacity: 0.4 },
      },
      {
        type: 'line',
        data: lineData,
        lineStyle: { color: CHART_LINE_4, type: 'dashed', width: 2 },
        symbol: 'none',
      },
      {
        type: 'line',
        markLine: {
          silent: true,
          data: [[{ xAxis: 1 }, { xAxis: 1 }]],
          lineStyle: { color: '#999', type: 'dotted' },
          label: { formatter: 'RPA=1', fontSize: 10 },
        },
        data: [],
      },
    ],
  };
}

export function buildRpaSegmentBoxOption(
  segments: string[],
  boxData: Record<string, number[]>,
  stats: { segment: string; mean: number; median: number; std: number; count: number }[],
): EChartsOption {
  const seriesData: number[][] = [];
  const outlierData: number[][] = [];
  const xData: string[] = [];

  for (const seg of segments) {
    const values = (boxData[seg] ?? []).slice().sort((a, b) => a - b);
    if (values.length < 5) continue;
    const st = stats.find((s) => s.segment === seg);
    const q1 = values[Math.floor(values.length * 0.25)];
    const q3val = values[Math.floor(values.length * 0.75)];
    const med = st?.median ?? values[Math.floor(values.length * 0.5)];
    const iqr = q3val - q1;
    const lower = q1 - 1.5 * iqr;
    const upper = q3val + 1.5 * iqr;
    const whiskerLow = Math.max(lower, values[0]);
    const whiskerHigh = Math.min(upper, values[values.length - 1]);
    seriesData.push([whiskerLow, q1, med, q3val, whiskerHigh]);
    values.forEach((v) => {
      if (v < lower || v > upper) outlierData.push([xData.length, v]);
    });
    xData.push(seg);
  }

  return {
    tooltip: { trigger: 'item' },
    grid: { top: 20, right: 30, bottom: 60, left: 80 },
    xAxis: { type: 'category', data: xData, name: 'RPA 分段', nameLocation: 'middle', nameGap: 40, axisLabel: { rotate: 15 } },
    yAxis: { type: 'value', name: '票价（元）', nameLocation: 'middle', nameGap: 65 },
    series: [
      {
        name: '票价分布',
        type: 'boxplot',
        data: seriesData,
        itemStyle: { color: 'rgba(44,62,80,0.6)', borderColor: CHART_LINE_1 },
      },
      {
        name: '异常值',
        type: 'scatter',
        large: true,
        data: outlierData,
        symbolSize: 3,
        itemStyle: { color: '#95A5A6', opacity: 0.5 },
      },
    ],
  };
}

export function buildSupplyEffectOption(
  scatterData: { label: string; r: number; p: number; tension: number[]; price: number[] }[],
): EChartsOption {
  const series: EChartsOption['series'] = scatterData.map((item, i) => ({
    name: item.label,
    type: 'scatter',
    large: true,
    data: item.tension.map((t, j) => [t, item.price[j]]),
    symbolSize: 5,
    itemStyle: { color: i === 0 ? 'steelblue' : 'coral', opacity: 0.5 },
  }));
  const regressionSeries: EChartsOption['series'] = scatterData.map((item, i) => {
    const n = item.tension.length;
    if (n < 2) return { type: 'line', data: [], symbol: 'none' };
    const sumX = item.tension.reduce((a, b) => a + b, 0);
    const sumY = item.price.reduce((a, b) => a + b, 0);
    const sumXY = item.tension.reduce((a, b, j) => a + b * item.price[j], 0);
    const sumX2 = item.tension.reduce((a, b) => a + b * b, 0);
    const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
    const intercept = (sumY - slope * sumX) / n;
    const minX = Math.min(...item.tension);
    const maxX = Math.max(...item.tension);
    return {
      name: `${item.label}趋势`,
      type: 'line',
      data: [[minX, slope * minX + intercept], [maxX, slope * maxX + intercept]],
      lineStyle: { color: i === 0 ? 'steelblue' : 'coral', type: 'dashed', width: 2 },
      symbol: 'none',
    };
  });

  return {
    tooltip: { trigger: 'item' },
    legend: { ...LEGEND_TOP_RIGHT },
    grid: { top: 40, right: 30, bottom: 50, left: 80 },
    xAxis: { type: 'value', name: '高铁供给紧张度 (0-1)', min: 0, max: 1, nameLocation: 'middle', nameGap: 40 },
    yAxis: { type: 'value', name: '航空票价（元）', nameLocation: 'middle', nameGap: 65 },
    series: [...(Array.isArray(series) ? series : [series]), ...(Array.isArray(regressionSeries) ? regressionSeries : [regressionSeries])],
  };
}

export function buildNShapeOption(
  nShapeData: {
    start: string;
    end: string;
    air_rel_days: number[];
    air_prices: number[];
    hsr_rel_days?: number[];
    hsr_prices?: (number | null)[];
  }[],
): EChartsOption {
  const series: EChartsOption['series'] = [];
  nShapeData.forEach((item) => {
    series.push({
      name: `航空 (${item.start}~${item.end})`,
      type: 'line',
      data: item.air_rel_days.map((d, i) => [d, item.air_prices[i]]),
      lineStyle: { width: 1.5 },
      symbolSize: 5,
      itemStyle: { color: CHART_LINE_1 },
    } as never);
    if (item.hsr_rel_days && item.hsr_prices) {
      series.push({
        name: `高铁商务座 (${item.start}~${item.end})`,
        type: 'line',
        data: item.hsr_rel_days.map((d, i) => [d, item.hsr_prices![i]]),
        lineStyle: { width: 1.2, type: 'dashed' },
        symbolSize: 4,
        symbol: 'square',
        itemStyle: { color: CHART_LINE_4 },
      } as never);
    }
  });

  return {
    tooltip: { trigger: 'axis' },
    legend: { type: 'scroll', ...LEGEND_TOP_RIGHT },
    grid: { top: 40, right: 30, bottom: 50, left: 80 },
    xAxis: { type: 'value', name: '相对节假日位置（天）', nameLocation: 'middle', nameGap: 35 },
    yAxis: { type: 'value', name: '票价（元）', nameLocation: 'middle', nameGap: 65 },
    series,
  };
}

export function buildExpoEffectOption(
  dayTypes: string[],
  nonExpo: number[],
  expo: number[],
): EChartsOption {
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['非展会日', '展会日'], ...LEGEND_TOP_RIGHT },
    grid: { top: 40, right: 30, bottom: 30, left: 80 },
    xAxis: { type: 'category', data: dayTypes },
    yAxis: { type: 'value', name: '平均票价（元）', nameLocation: 'middle', nameGap: 65 },
    series: [
      {
        name: '非展会日',
        type: 'bar',
        data: nonExpo,
        barWidth: '30%',
        itemStyle: { color: CHART_LINE_1 },
        label: { show: true, position: 'top', formatter: '{c}', fontSize: 10 },
      },
      {
        name: '展会日',
        type: 'bar',
        data: expo,
        barWidth: '30%',
        itemStyle: { color: CHART_LINE_4 },
        label: { show: true, position: 'top', formatter: '{c}', fontSize: 10 },
      },
    ],
  };
}

export function buildWindowedRpaOption(
  windowData: {
    window: string;
    dates: string[];
    air_avg: number[];
    rpa_avg: number[];
    weekends: number[];
    holidays?: { start: number; end: number };
  }[],
): EChartsOption[] {
  return windowData.map((w) => {
    const markAreaPairs = buildMarkAreaPairs(w.dates, w.weekends, w.holidays);
    return {
      title: { text: w.window, left: 'center', textStyle: { fontSize: 13, fontWeight: 'bold' } },
      tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
      legend: { data: ['航空均价', 'RPA'], ...LEGEND_TOP_RIGHT },
      grid: { top: 50, right: 80, bottom: 80, left: 80 },
      dataZoom: TIME_SERIES_DATAZOOM,
      xAxis: { type: 'category', data: w.dates, axisLabel: { formatter: (v: string) => v.slice(5) } },
      yAxis: [
        { type: 'value', name: '航空（元）', position: 'left', nameLocation: 'middle', nameGap: 65, scale: true },
        { type: 'value', name: 'RPA', position: 'right', nameLocation: 'middle', nameGap: 55 },
      ],
      series: [
        {
          name: '航空均价',
          type: 'line',
          data: w.air_avg,
          yAxisIndex: 0,
          lineStyle: { width: 1.5 },
          symbolSize: 3,
          itemStyle: { color: CHART_LINE_1 },
          markArea: markAreaPairs.length > 0 ? { silent: true, data: markAreaPairs } : undefined,
        },
        {
          name: 'RPA',
          type: 'line',
          data: w.rpa_avg,
          yAxisIndex: 1,
          lineStyle: { width: 1.5, type: 'dashed' },
          symbolSize: 3,
          symbol: 'square',
          itemStyle: { color: CHART_LINE_3 },
        },
      ],
    };
  });
}

export function buildRpaElasticityOption(
  elasticity: {
    window: string;
    coef_scaled: number | null;
    std_err_scaled: number | null;
    p_value: number | null;
  }[],
): EChartsOption {
  const windows = elasticity.map((e) => e.window);
  const values = elasticity.map((e) => e.coef_scaled ?? 0);
  const barColors = [CHART_LINE_1, CHART_LINE_3, CHART_LINE_2];

  return {
    tooltip: {
      trigger: 'axis',
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      formatter(params: any) {
        const p = Array.isArray(params) ? params[0] : params;
        const idx = p.dataIndex as number;
        const e = elasticity[idx];
        if (!e || e.coef_scaled == null) return '';
        const sig = e.p_value != null && e.p_value < 0.05 ? ' *' : '';
        return `${e.window}<br/>系数: ${e.coef_scaled}${sig}<br/>标准误: ${e.std_err_scaled}<br/>p值: ${e.p_value}`;
      },
    },
    grid: { top: 40, right: 30, bottom: 40, left: 100 },
    xAxis: { type: 'value', name: '航空均价变动（元/RPA增加0.1）', nameLocation: 'middle', nameGap: 40 },
    yAxis: { type: 'category', data: windows },
    series: [{
      name: '弹性系数',
      type: 'bar',
      data: values.map((v, i) => ({
        value: v,
        itemStyle: { color: barColors[i % barColors.length] },
      })),
      barWidth: '40%',
      label: {
        show: true,
        position: 'right',
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        formatter(params: any) {
          const idx = params.dataIndex as number;
          const e = elasticity[idx];
          if (!e || e.coef_scaled == null) return '';
          const sig = e.p_value != null && e.p_value < 0.05 ? '*' : '';
          return `${e.coef_scaled}${sig}`;
        },
        fontSize: 10,
      },
    }],
  };
}
