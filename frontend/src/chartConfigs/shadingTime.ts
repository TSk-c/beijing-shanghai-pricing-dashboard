import type { EChartsOption } from 'echarts';
import {
  BG_PRIMARY,
  CHART_LINE_1,
  HOLIDAY_SHADE,
  INFO,
  TEXT_PRIMARY,
  WEEKEND_SHADE,
} from '../constants/colors';
import type { ShadingTimeSeriesInput } from '../types/charts';

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
  holidays: ShadingTimeSeriesInput['holidays'],
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
      {
        name: '节假日',
        xAxis: dates[holidays.start],
        itemStyle: { color: HOLIDAY_SHADE },
      },
      { xAxis: dates[holidays.end] },
    ]);
  }
  return data;
}

/** 单 Y 轴面积时序图（阴影区域 + 周末/节假日 markArea） */
export function shadingTimeConfig(input: ShadingTimeSeriesInput): EChartsOption {
  const name = input.seriesName ?? '序列';
  const yName = input.yAxisName ?? '数值';
  const markAreaPairs = buildMarkAreaPairs(input.dates, input.weekends, input.holidays);

  return {
    color: [CHART_LINE_1],
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: {
      top: 10,
      right: 10,
      selectedMode: true,
      backgroundColor: 'rgba(255,255,255,0.9)',
    },
    grid: { top: 56, right: 48, bottom: 80, left: 80 },
    dataZoom: [
      { type: 'inside', xAxisIndex: 0, filterMode: 'none' },
      { type: 'slider', xAxisIndex: 0, height: 22, bottom: 16, filterMode: 'none' },
    ],
    xAxis: {
      type: 'category',
      data: input.dates,
      axisLabel: { formatter: (v: string) => v.slice(5) },
    },
    yAxis: {
      type: 'value',
      name: yName,
      nameTextStyle: { color: TEXT_PRIMARY },
      axisLine: { lineStyle: { color: CHART_LINE_1 } },
      splitLine: { lineStyle: { color: 'rgba(178, 186, 187, 0.35)' } },
    },
    series: [
      {
        name,
        type: 'line',
        data: input.values,
        smooth: true,
        symbol: 'none',
        lineStyle: { color: CHART_LINE_1, width: 2 },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(44, 62, 80, 0.35)' },
              { offset: 1, color: 'rgba(41, 128, 185, 0.08)' },
            ],
          },
        },
        itemStyle: { color: INFO },
        markArea:
          markAreaPairs.length > 0
            ? {
                silent: true,
                data: markAreaPairs,
              }
            : undefined,
      },
    ],
    backgroundColor: BG_PRIMARY,
  };
}
