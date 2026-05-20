import { useEffect, useMemo, useState } from 'react';
import { Button, Card, Col, Result, Row, Skeleton, Typography } from 'antd';
import { EchartsBox } from '../components/EchartsBox';
import { RpaCorrelationChart } from '../components/RpaCorrelationChart';
import { fetchEdaCharts, fetchRpaTrend } from '../services/api';
import { mockRpaTrend } from '../services/mockData';
import type { EdaChartsResponse } from '../types/api';
import type { DualAxisTimeSeriesInput } from '../types/charts';
import {
  buildRpaElasticityOption,
  buildRpaHeteroOption,
  buildRpaSegmentBoxOption,
  buildWindowedRpaOption,
} from '../chartConfigs/edaCharts';

const fallbackTrend: DualAxisTimeSeriesInput = {
  dates: [...mockRpaTrend.dates],
  airPrices: [...mockRpaTrend.airPrices],
  rpaValues: [...mockRpaTrend.rpaValues],
  weekends: [...mockRpaTrend.weekends],
  holidays: { ...mockRpaTrend.holidays },
  pearsonR: mockRpaTrend.pearson_r,
  pearsonP: mockRpaTrend.pearson_p,
};

export function RpaAnalysisPage() {
  const [edaData, setEdaData] = useState<EdaChartsResponse | null>(null);
  const [trendData, setTrendData] = useState<DualAxisTimeSeriesInput>(fallbackTrend);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [eda, trend] = await Promise.all([fetchEdaCharts(), fetchRpaTrend()]);
        if (!cancelled) {
          setEdaData(eda);
          setTrendData({
            dates: [...trend.dates],
            airPrices: [...trend.airPrices],
            rpaValues: [...trend.rpaValues],
            weekends: [...trend.weekends],
            holidays: trend.holidays ? { ...trend.holidays } : undefined,
            pearsonR: trend.pearson_r ?? null,
            pearsonP: trend.pearson_p ?? null,
          });
        }
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
        const [eda, trend] = await Promise.all([fetchEdaCharts(), fetchRpaTrend()]);
        if (!cancelled) {
          setEdaData(eda);
          setTrendData({
            dates: [...trend.dates],
            airPrices: [...trend.airPrices],
            rpaValues: [...trend.rpaValues],
            weekends: [...trend.weekends],
            holidays: trend.holidays ? { ...trend.holidays } : undefined,
            pearsonR: trend.pearson_r ?? null,
            pearsonP: trend.pearson_p ?? null,
          });
        }
      } catch {
        if (!cancelled) setError('数据加载失败');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  };

  const pearsonText =
    trendData.pearsonR != null && trendData.pearsonP != null
      ? `Pearson r = ${trendData.pearsonR.toFixed(3)}, p = ${trendData.pearsonP.toFixed(4)}`
      : null;

  const heteroOptions = useMemo(() => {
    if (!edaData) return [];
    return edaData.rpa_heterogeneity.map((item) =>
      buildRpaHeteroOption(item.period, item.scatter_rpa, item.scatter_price, item.r, item.p, item.slope),
    );
  }, [edaData]);

  const segmentOption = useMemo(() => {
    if (!edaData || !edaData.rpa_segment.segments.length) return {};
    return buildRpaSegmentBoxOption(
      edaData.rpa_segment.segments,
      edaData.rpa_segment.box_data,
      edaData.rpa_segment.stats,
    );
  }, [edaData]);

  const windowedRpaOptions = useMemo(() => {
    if (!edaData || !edaData.windowed_rpa.length) return [];
    return buildWindowedRpaOption(edaData.windowed_rpa);
  }, [edaData]);

  const elasticityOption = useMemo(() => {
    if (!edaData || !edaData.rpa_elasticity.length) return {};
    return buildRpaElasticityOption(edaData.rpa_elasticity);
  }, [edaData]);

  if (loading) return <Skeleton active paragraph={{ rows: 8 }} style={{ padding: 24 }} />;
  if (error) return <Result status="error" title={error} extra={<Button type="primary" onClick={refetch}>重试</Button>} />;

  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={4} style={{ marginTop: 0 }}>
        RPA 综合分析
      </Typography.Title>
      <Typography.Paragraph type="secondary">
        RPA（高铁-航空价格比）时序走势、分提前期异质性、阈值效应。
      </Typography.Paragraph>

      <Card title="高铁相对价格优势 (RPA) 与航空票价走势" styles={{ body: { paddingTop: 8 } }}>
        <Typography.Paragraph type="secondary" style={{ marginBottom: 8, fontSize: 12 }}>
          黑线为航空日均价（左轴），蓝虚线为 RPA（右轴）；浅蓝/浅橙区域分别为周末与节假日示意。
          {pearsonText && <> 相关性：{pearsonText}</>}
        </Typography.Paragraph>
        <RpaCorrelationChart data={trendData} height={480} />
      </Card>

      {heteroOptions.length > 0 && (
        <Card title="RPA 与航空票价的相关性：分提前期异质性" style={{ marginTop: 16 }} styles={{ body: { paddingTop: 8 } }}>
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

      {edaData && edaData.rpa_segment.segments.length > 0 && (
        <Card title="航空票价分布：按 RPA 分段" style={{ marginTop: 16 }} styles={{ body: { paddingTop: 8 } }}>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 8, fontSize: 12 }}>
            按 RPA 分段展示航空票价的箱线图分布，RPA 越高表示高铁相对越贵。
          </Typography.Paragraph>
          <EchartsBox option={segmentOption} height={420} />
        </Card>
      )}

      {windowedRpaOptions.length > 0 && (
        <Card title="分提前窗口航空均价与 RPA 对比（0-14天有效数据）" style={{ marginTop: 16 }} styles={{ body: { paddingTop: 8 } }}>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 8, fontSize: 12 }}>
            按提前期窗口分列，左轴为航空均价，右轴为 RPA；浅蓝/浅橙区域为周末与节假日。可缩放交互。
          </Typography.Paragraph>
          <Row gutter={[12, 12]}>
            {windowedRpaOptions.map((opt, i) => (
              <Col xs={24} key={i}>
                <EchartsBox option={opt} height={320} />
              </Col>
            ))}
          </Row>
        </Card>
      )}

      {edaData && edaData.rpa_elasticity.length > 0 && (
        <Card title="分窗口 RPA 弹性系数（0-14天细分）" style={{ marginTop: 16 }} styles={{ body: { paddingTop: 8 } }}>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 8, fontSize: 12 }}>
            柱状图展示 RPA 每增加 0.1 对航空均价的影响（回归系数），* 表示 p &lt; 0.05 显著。
          </Typography.Paragraph>
          <EchartsBox option={elasticityOption} height={280} />
        </Card>
      )}
    </div>
  );
}
