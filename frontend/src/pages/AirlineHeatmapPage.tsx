import { useEffect, useMemo, useState } from 'react';
import { Button, Card, Result, Skeleton, Typography } from 'antd';
import { EchartsBox } from '../components/EchartsBox';
import { fetchEdaCharts } from '../services/api';
import type { EdaChartsResponse } from '../types/api';
import {
  buildAirlineCurvesOption,
  buildHeatmapOption,
} from '../chartConfigs/edaCharts';

export function AirlineHeatmapPage() {
  const [data, setData] = useState<EdaChartsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const d = await fetchEdaCharts();
        if (!cancelled) setData(d);
      } catch {
        if (!cancelled) setError('数据加载失败');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const refetch = () => {
    setLoading(true);
    setError(null);
    let cancelled = false;
    (async () => {
      try {
        const d = await fetchEdaCharts();
        if (!cancelled) setData(d);
      } catch {
        if (!cancelled) setError('数据加载失败');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  };

  const airlineOption = useMemo(() => {
    if (!data) return {};
    return buildAirlineCurvesOption(data.airlines, data.airline_curves);
  }, [data]);

  const heatmapOption = useMemo(() => {
    if (!data) return {};
    return buildHeatmapOption(data.heatmap.dow_names, data.heatmap.columns, data.heatmap.matrix);
  }, [data]);

  if (loading) return <Skeleton active paragraph={{ rows: 8 }} style={{ padding: 24 }} />;
  if (error) return <Result status="error" title={error} extra={<Button type="primary" onClick={refetch}>重试</Button>} />;

  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={4} style={{ marginTop: 0 }}>
        航司预订曲线与周内效应
      </Typography.Title>
      <Typography.Paragraph type="secondary">
        各航司票价随提前天数的变化趋势，以及出发星期×提前期热力图，验证周五高峰/周六低谷效应。
      </Typography.Paragraph>

      <Card title="各航司票价随提前天数变化（0-30天）" styles={{ body: { paddingTop: 8 } }}>
        <Typography.Paragraph type="secondary" style={{ marginBottom: 8, fontSize: 12 }}>
          每条线代表一个航司的平均票价曲线，对比不同航司的定价策略差异。
        </Typography.Paragraph>
        <EchartsBox option={airlineOption} height={420} />
      </Card>

      <Card title="周内效应 × 提前期热力图" style={{ marginTop: 16 }} styles={{ body: { paddingTop: 8 } }}>
        <Typography.Paragraph type="secondary" style={{ marginBottom: 8, fontSize: 12 }}>
          颜色越深表示平均票价越高；验证周五高峰和周六低谷效应在不同提前期的表现。
        </Typography.Paragraph>
        <EchartsBox option={heatmapOption} height={380} />
      </Card>
    </div>
  );
}
