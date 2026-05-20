import type { EChartsOption } from 'echarts';
import {
  CHART_LINE_1,
  CHART_LINE_2,
  HOLIDAY_SHADE,
  TEXT_PRIMARY,
  WEEKEND_SHADE,
} from '../constants/colors';
import type { DualAxisTimeSeriesInput } from '../types/charts';

type MarkAreaPair = [
  { name: string; xAxis: string; itemStyle?: { color: string } },
  { xAxis: string },
];

function groupConsecutive(sorted: number[]): [number, number][] {
  if (sorted.length === 0) {
    return [];
  }
  const ranges: [number, number][] = [];
  let lo = sorted[0];
  let hi = sorted[0];
  for (let i = 1; i < sorted.length; i++) {
    const v = sorted[i];
    if (v === hi + 1) {
      hi = v;
    } else {
      ranges.push([lo, hi]);
      lo = hi = v;
    }
  }
  ranges.push([lo, hi]);
  return ranges;
}

function buildMarkAreaPairs(
  dates: string[],
  weekends: number[] | undefined,
  holidays: DualAxisTimeSeriesInput['holidays'],
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

export function rpaCorrelationConfig(data: DualAxisTimeSeriesInput): EChartsOption {
  const markAreaPairs = buildMarkAreaPairs(data.dates, data.weekends, data.holidays);

  return {
    color: [CHART_LINE_1, CHART_LINE_2],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (params: unknown) => {
        const list = Array.isArray(params) ? params : [params];
        if (list.length === 0) {
          return '';
        }
        const head = list[0] as { axisValueLabel?: string; axisValue?: string };
        const dateLabel = head.axisValueLabel ?? head.axisValue ?? '';
        const lines = [`<div style="font-weight:600;margin-bottom:4px">${dateLabel}</div>`];
        for (const raw of list) {
          const p = raw as { marker?: string; seriesName?: string; value?: number | number[] };
          const v = Array.isArray(p.value) ? p.value[1] : p.value;
          if (typeof v !== 'number' || Number.isNaN(v)) {
            continue;
          }
          const name = p.seriesName ?? '';
          const decimals = name === 'RPA' ? 3 : 1;
          lines.push(`${p.marker ?? ''} ${name}：${v.toFixed(decimals)}`);
        }
        return lines.join('<br/>');
      },
    },
    legend: {
      top: 10,
      right: 10,
      selectedMode: true,
      backgroundColor: 'rgba(255,255,255,0.9)',
    },
    grid: { top: 64, right: 72, bottom: 80, left: 80 },
    dataZoom: [
      { type: 'inside', xAxisIndex: 0, filterMode: 'none' },
      { type: 'slider', xAxisIndex: 0, height: 22, bottom: 16, filterMode: 'none' },
    ],
    xAxis: {
      type: 'category',
      data: data.dates,
      axisLabel: { formatter: (v: string) => v.slice(5) },
    },
    yAxis: [
      {
        type: 'value',
        name: '航空票价（元）',
        position: 'left',
        axisLine: { lineStyle: { color: CHART_LINE_1 } },
        nameTextStyle: { color: TEXT_PRIMARY },
        scale: true,
      },
      {
        type: 'value',
        name: 'RPA',
        position: 'right',
        axisLine: { lineStyle: { color: CHART_LINE_2 } },
        splitLine: { show: false },
        nameTextStyle: { color: TEXT_PRIMARY },
      },
    ],
    series: [
      {
        name: '航空日均价',
        type: 'line',
        data: data.airPrices,
        smooth: true,
        yAxisIndex: 0,
        lineStyle: { color: CHART_LINE_1, width: 2.5, type: 'solid' },
        itemStyle: { color: CHART_LINE_1 },
        markArea:
          markAreaPairs.length > 0
            ? { silent: true, data: markAreaPairs }
            : undefined,
      },
      {
        name: 'RPA',
        type: 'line',
        yAxisIndex: 1,
        data: data.rpaValues,
        smooth: true,
        lineStyle: { color: CHART_LINE_2, width: 2, type: 'dashed' },
        itemStyle: { color: CHART_LINE_2 },
      },
    ],
  };
}
