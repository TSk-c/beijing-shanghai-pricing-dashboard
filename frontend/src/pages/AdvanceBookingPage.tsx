import { useEffect, useMemo, useState } from 'react';
import { Button, Card, Result, Skeleton, Typography } from 'antd';
import { EchartsBox } from '../components/EchartsBox';
import { fetchEdaCharts } from '../services/api';
import type { EdaChartsResponse } from '../types/api';
import {
  buildBoxPlotOption,
  buildQuantileCurveOption,
  buildTypicalDatesOption,
} from '../chartConfigs/edaCharts';

export function AdvanceBookingPage() {
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

  const quantileOption = useMemo(() => {
    if (!data) return {};
    return buildQuantileCurveOption(
      data.quantile_curve.days,
      data.quantile_curve.p10,
      data.quantile_curve.p25,
      data.quantile_curve.p50,
      data.quantile_curve.p75,
      data.quantile_curve.p90,
    );
  }, [data]);

  const typicalOption = useMemo(() => {
    if (!data) return {};
    return buildTypicalDatesOption(data.typical_dates);
  }, [data]);

  const boxOption = useMemo(() => {
    if (!data) return {};
    return buildBoxPlotOption(
      data.box_plot.bins,
      data.box_plot.box_data,
      data.box_plot.stats,
      data.box_plot.overall_median,
    );
  }, [data]);

  if (loading) return <Skeleton active paragraph={{ rows: 8 }} style={{ padding: 24 }} />;
  if (error) return <Result status="error" title={error} extra={<Button type="primary" onClick={refetch}>重试</Button>} />;

  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={4} style={{ marginTop: 0 }}>
        提前天数结构性分析
      </Typography.Title>
      <Typography.Paragraph type="secondary">
        分析票价随提前购买天数的变化规律：分位数扩散趋势、典型日期预订曲线、不同提前区间的票价分布。
      </Typography.Paragraph>

      <Card title="典型出发日期的预订曲线" styles={{ body: { paddingTop: 8 } }}>
        <Typography.Paragraph type="secondary" style={{ marginBottom: 8, fontSize: 12 }}>
          选取普通周三、周五、节前高峰、节假日中等典型日期，展示单日票价随提前天数的变化。
        </Typography.Paragraph>
        <EchartsBox option={typicalOption} height={420} />
      </Card>

      <Card title="票价分位数随提前天数的变化（0-30天）" style={{ marginTop: 16 }} styles={{ body: { paddingTop: 8 } }}>
        <Typography.Paragraph type="secondary" style={{ marginBottom: 8, fontSize: 12 }}>
          深色粗线为中位数，浅色细线为 P10/P90 和 P25/P75；越接近出发日，票价分布越宽。
        </Typography.Paragraph>
        <EchartsBox option={quantileOption} height={420} />
      </Card>

      <Card title="不同提前天区间的经济舱票价分布" style={{ marginTop: 16 }} styles={{ body: { paddingTop: 8 } }}>
        <Typography.Paragraph type="secondary" style={{ marginBottom: 8, fontSize: 12 }}>
          箱线图展示各提前天数区间的票价分布：箱体为 Q1-Q3，横线为中位数，须线为 1.5×IQR 范围。
        </Typography.Paragraph>
        <EchartsBox option={boxOption} height={420} />
      </Card>
    </div>
  );
}
