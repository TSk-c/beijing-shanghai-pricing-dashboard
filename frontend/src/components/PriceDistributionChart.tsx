import { useEffect, useMemo, useRef } from 'react';
import * as echarts from 'echarts';
import type { EChartsOption } from 'echarts';
import { priceDistributionConfig } from '../chartConfigs/priceDistribution';
import type { PriceDistributionInput } from '../types/priceDistribution';

export interface PriceDistributionChartProps {
  data: PriceDistributionInput;
  height?: number;
}

export function PriceDistributionChart({ data, height = 420 }: PriceDistributionChartProps) {
  const hostRef = useRef<HTMLDivElement>(null);

  const option = useMemo<EChartsOption>(() => priceDistributionConfig(data), [data]);

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
