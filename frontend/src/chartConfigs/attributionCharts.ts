import type { EChartsOption } from 'echarts';
import {
  BG_PRIMARY,
  CHART_LINE_1,
  CHART_LINE_2,
  CHART_LINE_3,
  CHART_LINE_4,
  CHART_LINE_5,
  SHAP_HIGH,
  SHAP_LOW,
  SHAP_NEUTRAL,
  TEXT_PRIMARY,
  TEXT_MUTED,
} from '../constants/colors';
import type { ShapWaterfallItem } from '../types/api';

export const CATEGORY_COLORS: Record<string, string> = {
  '提前期': CHART_LINE_1,
  '时间特征': CHART_LINE_2,
  '节假日/展会': CHART_LINE_3,
  '航班属性': CHART_LINE_4,
  '高铁竞争': CHART_LINE_5,
  '展会冲击': CHART_LINE_3,
  '其他': SHAP_NEUTRAL,
};

export function buildShapWaterfallOption(
  items: ShapWaterfallItem[],
): EChartsOption {
  const sorted = [...items].sort((a, b) => a.shap_value - b.shap_value);
  const features = sorted.map((s) => s.feature);
  const values = sorted.map((s) => s.shap_value);
  const colors = sorted.map((s) => s.shap_value >= 0 ? SHAP_HIGH : SHAP_LOW);

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: 'rgba(255,255,255,0.96)',
      borderColor: '#E0E0E0',
      textStyle: { color: TEXT_PRIMARY, fontSize: 12 },
      formatter(params: unknown) {
        const p = Array.isArray(params) ? params[0] : params;
        const idx = (p as { dataIndex?: number }).dataIndex ?? 0;
        const item = sorted[idx];
        const cat = item.category;
        const dir = item.shap_value >= 0 ? '推高' : '压低';
        return `<b>${item.feature}</b><br/>` +
          `类别：${cat}<br/>` +
          `SHAP值：${item.shap_value.toFixed(1)}（${dir}定价）`;
      },
    },
    grid: { left: 120, right: 30, top: 20, bottom: 48 },
    xAxis: {
      type: 'value',
      name: 'SHAP 值（元）',
      nameLocation: 'middle',
      nameGap: 32,
      nameTextStyle: { color: TEXT_MUTED, fontSize: 12 },
      axisLabel: { color: TEXT_MUTED, fontSize: 11 },
      splitLine: { lineStyle: { type: 'dashed', color: '#E8E8E8' } },
    },
    yAxis: {
      type: 'category',
      data: features,
      axisLabel: { color: TEXT_PRIMARY, fontSize: 11 },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: [
      {
        type: 'bar',
        data: values.map((v, i) => ({
          value: v,
          itemStyle: {
            color: colors[i],
            borderRadius: v >= 0 ? [0, 4, 4, 0] : [4, 0, 0, 4],
          },
        })),
        barWidth: '60%',
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { color: SHAP_NEUTRAL, type: 'dashed' },
          data: [{ xAxis: 0 }],
          label: { show: false },
        },
      },
    ],
    backgroundColor: BG_PRIMARY,
  };
}

export function buildCategoryContributionOption(
  categorySummary: Record<string, { total_abs_contribution: number; net_contribution: number }>,
): EChartsOption {
  const categories = Object.keys(categorySummary);
  const absValues = categories.map((c) => categorySummary[c].total_abs_contribution);
  const netValues = categories.map((c) => categorySummary[c].net_contribution);
  const barColors = categories.map((c) => CATEGORY_COLORS[c] ?? SHAP_NEUTRAL);

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: 'rgba(255,255,255,0.96)',
      borderColor: '#E0E0E0',
      textStyle: { color: TEXT_PRIMARY, fontSize: 12 },
      formatter(params: unknown) {
        const list = Array.isArray(params) ? params : [params];
        const catIdx = (list[0] as { dataIndex?: number }).dataIndex ?? 0;
        const cat = categories[catIdx];
        let html = `<b>${cat}</b><br/>`;
        for (const p of list) {
          const s = p as { seriesName?: string; value?: number; color?: string };
          html += `<span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:${s.color};margin-right:6px;"></span>`;
          html += `${s.seriesName}：${s.value?.toFixed(1) ?? '—'} 元<br/>`;
        }
        return html;
      },
    },
    legend: {
      data: [
        { name: '绝对贡献', itemStyle: { color: TEXT_MUTED, opacity: 0.35 } },
        { name: '净贡献', itemStyle: { color: TEXT_MUTED, opacity: 1 } },
        ...categories.map((cat, i) => ({ name: cat, itemStyle: { color: barColors[i] } })),
      ],
      top: 8,
      right: 10,
      itemWidth: 12,
      itemHeight: 12,
      itemGap: 12,
      textStyle: { color: TEXT_PRIMARY, fontSize: 11 },
    },
    grid: { left: 80, right: 40, top: 56, bottom: 48 },
    xAxis: {
      type: 'value',
      name: '贡献值（元）',
      nameLocation: 'middle',
      nameGap: 32,
      nameTextStyle: { color: TEXT_MUTED, fontSize: 12 },
      axisLabel: { color: TEXT_MUTED, fontSize: 11 },
      splitLine: { lineStyle: { type: 'dashed', color: '#E8E8E8' } },
    },
    yAxis: {
      type: 'category',
      data: categories,
      axisLabel: { color: TEXT_PRIMARY, fontSize: 12 },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: [
      {
        name: '绝对贡献',
        type: 'bar',
        data: absValues.map((v, i) => ({
          value: v,
          itemStyle: { color: barColors[i], opacity: 0.35, borderRadius: [0, 4, 4, 0] },
        })),
        barWidth: '30%',
      },
      {
        name: '净贡献',
        type: 'bar',
        data: netValues.map((v, i) => ({
          value: v,
          itemStyle: {
            color: barColors[i],
            opacity: 1,
            borderRadius: v >= 0 ? [0, 4, 4, 0] : [4, 0, 0, 4],
          },
        })),
        barWidth: '30%',
      },
    ],
    backgroundColor: BG_PRIMARY,
  };
}
