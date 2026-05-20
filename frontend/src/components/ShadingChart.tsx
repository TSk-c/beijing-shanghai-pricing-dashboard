import { useEffect, useMemo, useRef } from 'react';
import * as echarts from 'echarts';
import type { EChartsOption } from 'echarts';
import { shadingTimeConfig } from '../chartConfigs/shadingTime';
import type { ShadingTimeSeriesInput } from '../types/charts';

export interface ShadingChartProps {
  data: ShadingTimeSeriesInput;
  height?: number;
}

/** 单 Y 轴面积时序图（配置来自 chartConfigs/shadingTime） */
export function ShadingChart({ data, height = 360 }: ShadingChartProps) {
  const hostRef = useRef<HTMLDivElement>(null);

  const option = useMemo<EChartsOption>(() => shadingTimeConfig(data), [data]);

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
