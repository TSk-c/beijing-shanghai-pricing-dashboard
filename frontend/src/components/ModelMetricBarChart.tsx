import { useEffect, useMemo, useRef } from 'react';
import * as echarts from 'echarts';
import type { EChartsOption } from 'echarts';
import { modelComparisonBarConfig } from '../chartConfigs/modelComparisonBar';

export interface ModelMetricBarChartProps {
  models: string[];
  values: number[];
  metricName: string;
  height?: number;
}

/** 模型对比横向柱状图（每模型独立 series，支持图例显隐） */
export function ModelMetricBarChart({
  models,
  values,
  metricName,
  height = 320,
}: ModelMetricBarChartProps) {
  const hostRef = useRef<HTMLDivElement>(null);

  const option = useMemo<EChartsOption>(
    () => modelComparisonBarConfig(models, values, metricName),
    [models, values, metricName],
  );

  useEffect(() => {
    const el = hostRef.current;
    if (!el) {
      return;
    }
    const chart = echarts.init(el);
    chart.setOption(option, true);
    const onResize = () => chart.resize();
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
      chart.dispose();
    };
  }, [option]);

  return <div ref={hostRef} style={{ width: '100%', height }} />;
}
