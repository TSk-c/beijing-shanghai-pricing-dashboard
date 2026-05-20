import { useEffect, useMemo, useRef } from 'react';
import * as echarts from 'echarts';
import type { EChartsOption } from 'echarts';
import { dualAxisTimeConfig } from '../chartConfigs/dualAxisTime';
import type { DualAxisTimeSeriesInput } from '../types/charts';

export interface DualAxisChartProps {
  data: DualAxisTimeSeriesInput;
  /** 图表高度（px） */
  height?: number;
}

/** 双 Y 轴时序图（配置来自 chartConfigs/dualAxisTime） */
export function DualAxisChart({ data, height = 420 }: DualAxisChartProps) {
  const hostRef = useRef<HTMLDivElement>(null);

  const option = useMemo<EChartsOption>(() => dualAxisTimeConfig(data), [data]);

  useEffect(() => {
    const el = hostRef.current;
    if (!el) {
      return;
    }
    const chart = echarts.init(el);
    chart.setOption(option, true);
    const onResize = () => {
      chart.resize();
    };
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
      chart.dispose();
    };
  }, [option]);

  return <div ref={hostRef} style={{ width: '100%', height }} />;
}
