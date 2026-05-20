import { useEffect, useMemo, useRef } from 'react';
import * as echarts from 'echarts';
import type { EChartsOption } from 'echarts';
import { rpaTrendChartConfig } from '../chartConfigs/rpaTrendChart';
import type { RpaTrendChartInput } from '../types/rpaTrend';

export interface RpaTrendChartProps {
  data: RpaTrendChartInput;
  height?: number;
}

export function RpaTrendChart({ data, height = 460 }: RpaTrendChartProps) {
  const hostRef = useRef<HTMLDivElement>(null);

  const option = useMemo<EChartsOption>(() => rpaTrendChartConfig(data), [data]);

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
