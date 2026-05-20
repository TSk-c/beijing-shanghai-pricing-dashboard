import { useEffect, useMemo, useRef } from 'react';
import * as echarts from 'echarts';
import type { EChartsOption } from 'echarts';
import { rpaCorrelationConfig } from '../chartConfigs/rpaCorrelation';
import type { DualAxisTimeSeriesInput } from '../types/charts';

export interface RpaCorrelationChartProps {
  data: DualAxisTimeSeriesInput;
  height?: number;
}

export function RpaCorrelationChart({ data, height = 460 }: RpaCorrelationChartProps) {
  const hostRef = useRef<HTMLDivElement>(null);

  const option = useMemo<EChartsOption>(() => rpaCorrelationConfig(data), [data]);

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
