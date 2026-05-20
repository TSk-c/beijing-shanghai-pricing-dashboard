import { useEffect, useMemo, useRef } from 'react';
import * as echarts from 'echarts';
import type { EChartsOption } from 'echarts';
import { airHsrPriceComparisonConfig } from '../chartConfigs/airHsrPriceComparison';
import type { AirHsrPriceComparisonInput } from '../types/charts';

export interface AirHsrPriceComparisonChartProps {
  data: AirHsrPriceComparisonInput;
  height?: number;
}

export function AirHsrPriceComparisonChart({ data, height = 460 }: AirHsrPriceComparisonChartProps) {
  const hostRef = useRef<HTMLDivElement>(null);

  const option = useMemo<EChartsOption>(() => airHsrPriceComparisonConfig(data), [data]);

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
