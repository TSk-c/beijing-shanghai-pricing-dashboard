import { useEffect, useMemo, useState } from 'react';
import { Button, Card, Col, Result, Row, Skeleton, Typography } from 'antd';
import { EchartsBox } from '../components/EchartsBox';
import { fetchEdaCharts } from '../services/api';
import type { EdaChartsResponse } from '../types/api';
import {
  buildRpaHeteroOption,
  buildRpaSegmentBoxOption,
  buildSupplyEffectOption,
} from '../chartConfigs/edaCharts';

export function RpaDeepAnalysisPage() {
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

  const heteroOptions = useMemo(() => {
    if (!data) return [];
    return data.rpa_heterogeneity.map((item) =>
      buildRpaHeteroOption(item.period, item.scatter_rpa, item.scatter_price, item.r, item.p, item.slope),
    );
  }, [data]);

  const segmentOption = useMemo(() => {
    if (!data || !data.rpa_segment.segments.length) return {};
    return buildRpaSegmentBoxOption(
      data.rpa_segment.segments,
      data.rpa_segment.box_data,
      data.rpa_segment.stats,
    );
  }, [data]);

  const supplyEffectOption = useMemo(() => {
    if (!data || !data.supply_effect.scatter.length) return {};
    return buildSupplyEffectOption(data.supply_effect.scatter);
  }, [data]);

  if (loading) return <Skeleton active paragraph={{ rows: 8 }} style={{ padding: 24 }} />;
  if (error) return <Result status="error" title={error} extra={<Button type="primary" onClick={refetch}>重试</Button>} />;

  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={4} style={{ marginTop: 0 }}>
        RPA 深度分析
      </Typography.Title>
      <Typography.Paragraph type="secondary">
        RPA（高铁-航空价格比）与航空票价的相关性在不同提前期的异质性、RPA 阈值效应、供给紧张度条件效应。
      </Typography.Paragraph>

      {heteroOptions.length > 0 && (
        <Card title="RPA 与航空票价的相关性：分提前期异质性" styles={{ body: { paddingTop: 8 } }}>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 8, fontSize: 12 }}>
            每个子图对应一个提前期窗口，散点为 RPA vs 航空票价，红色虚线为线性回归拟合，灰色竖线为 RPA=1（价格持平）。
          </Typography.Paragraph>
          <Row gutter={[12, 12]}>
            {heteroOptions.map((opt, i) => (
              <Col xs={24} md={8} key={i}>
                <EchartsBox option={opt} height={340} />
              </Col>
            ))}
          </Row>
        </Card>
      )}

      {data && data.rpa_segment.segments.length > 0 && (
        <Card title="航空票价分布：按 RPA 分段" style={{ marginTop: 16 }} styles={{ body: { paddingTop: 8 } }}>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 8, fontSize: 12 }}>
            按 RPA 分段展示航空票价的箱线图分布，RPA 越高表示高铁相对越贵。
          </Typography.Paragraph>
          <EchartsBox option={segmentOption} height={400} />
        </Card>
      )}

      {data && data.supply_effect.scatter.length > 0 && (
        <Card title="供给紧张度对航空票价的影响：节假日 vs 工作日" style={{ marginTop: 16 }} styles={{ body: { paddingTop: 8 } }}>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 8, fontSize: 12 }}>
            散点图展示高铁供给紧张度与航空票价的关系，蓝色为工作日，红色为节假日；虚线为线性回归拟合。
          </Typography.Paragraph>
          <EchartsBox option={supplyEffectOption} height={420} />
        </Card>
      )}
    </div>
  );
}
