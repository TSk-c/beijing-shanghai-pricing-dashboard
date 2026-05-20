import { useEffect, useRef } from 'react';
import { Spin } from 'antd';
import type { EChartsOption } from 'echarts';
import * as echarts from 'echarts/core';
import { LineChart, ScatterChart, BarChart, HeatmapChart, BoxplotChart, RadarChart, PieChart } from 'echarts/charts';
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  VisualMapComponent,
  MarkLineComponent,
  DataZoomComponent,
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

echarts.use([
  LineChart, ScatterChart, BarChart, HeatmapChart, BoxplotChart, RadarChart, PieChart,
  TitleComponent, TooltipComponent, LegendComponent, GridComponent,
  VisualMapComponent, MarkLineComponent, DataZoomComponent, CanvasRenderer,
]);

interface EchartsBoxProps {
  option: EChartsOption;
  height?: number;
  loading?: boolean;
}

export function EchartsBox({ option, height = 400, loading = false }: EchartsBoxProps) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    if (!chartRef.current) {
      chartRef.current = echarts.init(ref.current);
    }
    if (!loading) {
      chartRef.current.setOption(option, true);
    }
  }, [option, loading]);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      chartRef.current?.resize();
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    return () => {
      chartRef.current?.dispose();
      chartRef.current = null;
    };
  }, []);

  return (
    <div style={{ position: 'relative', width: '100%', height }}>
      {loading && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 2,
            background: 'rgba(255,255,255,0.6)',
          }}
        >
          <Spin />
        </div>
      )}
      <div ref={ref} style={{ width: '100%', height }} />
    </div>
  );
}
