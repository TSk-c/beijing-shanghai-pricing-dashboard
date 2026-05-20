import type { EChartsOption } from 'echarts';
import {
  BG_PRIMARY,
  CHART_HISTOGRAM_BAR,
  KDE_LINE,
  MEAN_LINE,
  MEDIAN_LINE,
  TEXT_PRIMARY,
} from '../constants/colors';
import type { PriceDistributionInput } from '../types/priceDistribution';

function findBinIndexForPrice(bins: PriceDistributionInput['bins'], price: number): number {
  const idx = bins.findIndex((b) => price >= b.start && price < b.end);
  if (idx >= 0) {
    return idx;
  }
  let best = 0;
  let bestDist = Number.POSITIVE_INFINITY;
  bins.forEach((b, i) => {
    const mid = (b.start + b.end) / 2;
    const d = Math.abs(mid - price);
    if (d < bestDist) {
      bestDist = d;
      best = i;
    }
  });
  return best;
}

/**
 * 票价分布：直方图 + KDE 曲线（基于 docs/CHART_TEMPLATES 模板2）
 * 中位数/均值竖线：蓝虚线、黑虚线
 */
export function priceDistributionConfig(input: PriceDistributionInput): EChartsOption {
  const { bins, median, mean } = input;
  const mids = bins.map((b) => (b.start + b.end) / 2);
  const xLabels = mids.map((m) => String(m));

  const maxD = Math.max(...bins.map((b) => b.density), 1e-12);
  const norm = (d: number) => (d / maxD) * 100;
  const barHeights = bins.map((b) => norm(b.density));
  const kdeHeights = bins.map((b) => norm(b.density));

  const medianIdx = findBinIndexForPrice(bins, median);
  const meanIdx = findBinIndexForPrice(bins, mean);

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: unknown) => {
        const list = Array.isArray(params) ? params : [params];
        const first = list[0] as { dataIndex?: number };
        const i = first.dataIndex ?? 0;
        const b = bins[i];
        if (!b) {
          return '';
        }
        const lines = [
          `<div style="font-weight:600">票价区间 ${b.start}–${b.end} 元</div>`,
          `相对柱高：${barHeights[i]?.toFixed(2) ?? ''}`,
          `<span style="color:${KDE_LINE}">KDE（相对）：${kdeHeights[i]?.toFixed(4) ?? ''}</span>`,
        ];
        return lines.join('<br/>');
      },
    },
    legend: {
      top: 8,
      left: 'center',
      selectedMode: true,
    },
    grid: { top: 48, right: 24, bottom: 80, left: 72 },
    dataZoom: [
      { type: 'inside', xAxisIndex: 0, filterMode: 'none' },
      { type: 'slider', xAxisIndex: 0, height: 22, bottom: 12, filterMode: 'none' },
    ],
    xAxis: {
      type: 'category',
      data: xLabels,
      name: '票价（元，区间中点）',
      nameLocation: 'middle',
      nameGap: 36,
      axisLabel: { rotate: 45, interval: 7, color: TEXT_PRIMARY },
      nameTextStyle: { color: TEXT_PRIMARY },
    },
    yAxis: [
      {
        type: 'value',
        name: '相对频数',
        nameTextStyle: { color: TEXT_PRIMARY },
        axisLabel: { color: TEXT_PRIMARY },
      },
      {
        type: 'value',
        name: '核密度（相对）',
        splitLine: { show: false },
        nameTextStyle: { color: TEXT_PRIMARY },
        axisLabel: { color: TEXT_PRIMARY },
      },
    ],
    series: [
      {
        name: '票价分布（直方）',
        type: 'bar',
        data: barHeights,
        barMaxWidth: 14,
        itemStyle: { color: CHART_HISTOGRAM_BAR },
        markLine: {
          silent: true,
          symbol: 'none',
          data: [
            {
              name: '中位数',
              xAxis: xLabels[medianIdx],
              label: { formatter: `中位数=${median}元`, color: MEDIAN_LINE },
              lineStyle: { type: 'dashed', color: MEDIAN_LINE, width: 2 },
            },
            {
              name: '均值',
              xAxis: xLabels[meanIdx],
              label: { formatter: `均值=${mean}元`, color: MEAN_LINE },
              lineStyle: { type: 'dashed', color: MEAN_LINE, width: 2 },
            },
          ],
        },
      },
      {
        name: 'KDE',
        type: 'line',
        yAxisIndex: 1,
        data: kdeHeights,
        smooth: true,
        symbol: 'none',
        lineStyle: { color: KDE_LINE, width: 2 },
        itemStyle: { color: KDE_LINE },
      },
    ],
    backgroundColor: BG_PRIMARY,
  };
}
