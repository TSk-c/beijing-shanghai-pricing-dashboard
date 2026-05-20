import type { EChartsOption } from 'echarts';
import {
  CHART_LINE_1,
  CHART_LINE_2,
  CHART_LINE_3,
  CHART_LINE_4,
  INFO,
  WARNING,
} from '../constants/colors';

export function dailyRecordsTrendConfig(
  dates: string[],
  counts: number[],
  lowDates: string[],
): EChartsOption {
  const lowSet = new Set(lowDates);
  const markData = dates
    .map((d, i) => (lowSet.has(d) ? { name: '低覆盖', coord: [d, counts[i]] } : null))
    .filter(Boolean);

  return {
    color: [CHART_LINE_1],
    tooltip: { trigger: 'axis' },
    grid: { top: 24, right: 24, bottom: 60, left: 72 },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: { formatter: (v: string) => v.slice(5), rotate: 45 },
    },
    yAxis: { type: 'value', name: '记录数' },
    series: [
      {
        name: '每日采集记录数',
        type: 'line',
        data: counts,
        smooth: true,
        lineStyle: { color: CHART_LINE_1, width: 2 },
        itemStyle: { color: CHART_LINE_1 },
        markPoint: {
          data: markData as { name: string; coord: [string, number] }[],
          symbol: 'pin',
          symbolSize: 28,
          itemStyle: { color: WARNING },
          label: { fontSize: 10 },
        },
      },
    ],
  };
}

export function dailyFlightsTrendConfig(
  dates: string[],
  counts: number[],
): EChartsOption {
  return {
    color: [CHART_LINE_2],
    tooltip: { trigger: 'axis' },
    grid: { top: 24, right: 24, bottom: 60, left: 72 },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: { formatter: (v: string) => v.slice(5), rotate: 45 },
    },
    yAxis: { type: 'value', name: '航班数', min: 0 },
    series: [
      {
        name: '每日采集航班数',
        type: 'line',
        data: counts,
        smooth: true,
        areaStyle: { color: 'rgba(41, 128, 185, 0.15)' },
        lineStyle: { color: CHART_LINE_2, width: 2 },
        itemStyle: { color: CHART_LINE_2 },
      },
    ],
  };
}

export function airlineBarConfig(
  names: string[],
  counts: number[],
): EChartsOption {
  const wanData = counts.map((v) => v / 10000);
  return {
    color: [INFO],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: unknown) => {
        const p = (params as { name: string; value: number }[])[0];
        return `${p.name}<br/>记录数：${(p.value * 10000).toLocaleString('zh-CN')}`;
      },
    },
    grid: { top: 8, right: 60, bottom: 8, left: 100, containLabel: true },
    xAxis: {
      type: 'value',
      name: '万',
      min: 0,
      max: 7,
      interval: 1,
      axisLabel: { formatter: '{value}' },
    },
    yAxis: {
      type: 'category',
      data: names,
      axisLabel: { fontSize: 11 },
      inverse: true,
    },
    series: [
      {
        name: '记录数',
        type: 'bar',
        data: wanData,
        barMaxWidth: 28,
        itemStyle: {
          color: INFO,
          borderRadius: [0, 4, 4, 0],
        },
        label: {
          show: true,
          position: 'right',
          fontSize: 10,
          formatter: (p: unknown) => {
            const v = (p as { value: number }).value;
            return `${v.toFixed(1)}万`;
          },
        },
      },
    ] as EChartsOption['series'],
  };
}

export function airportPieConfig(
  names: string[],
  counts: number[],
): EChartsOption {
  return {
    color: [CHART_LINE_1, CHART_LINE_2, CHART_LINE_3, CHART_LINE_4],
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0 },
    series: [
      {
        name: '分布',
        type: 'pie',
        radius: ['42%', '68%'],
        center: ['50%', '46%'],
        data: names.map((n, i) => ({ name: n, value: counts[i] })),
        label: {
          show: true,
          position: 'inside',
          formatter: '{d}%',
          fontSize: 10,
          fontWeight: 'bold',
          color: '#fff',
          precision: 2,
        },
        labelLine: { show: false },
        emphasis: {
          itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.3)' },
        },
      },
    ],
  };
}

export function timeTypePieConfig(
  weekday: number,
  weekend: number,
  holiday: number,
): EChartsOption {
  const normalWeekday = weekday - holiday;
  return {
    color: [CHART_LINE_2, CHART_LINE_3, WARNING],
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0 },
    series: [
      {
        name: '时间类型',
        type: 'pie',
        radius: ['42%', '68%'],
        center: ['50%', '46%'],
        data: [
          { name: '工作日', value: normalWeekday },
          { name: '周末', value: weekend },
          { name: '节假日', value: holiday },
        ],
        label: {
          show: true,
          position: 'inside',
          formatter: '{b}\n{d}%',
          fontSize: 10,
          fontWeight: 'bold',
          color: '#fff',
          precision: 2,
        },
        labelLine: { show: false },
      },
    ],
  };
}
