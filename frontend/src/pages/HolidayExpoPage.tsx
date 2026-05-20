import { useEffect, useMemo, useState } from 'react';
import { Button, Card, Col, Descriptions, Result, Row, Skeleton, Typography } from 'antd';
import { EchartsBox } from '../components/EchartsBox';
import { fetchEdaCharts } from '../services/api';
import type { EdaChartsResponse } from '../types/api';
import { buildExpoEffectOption, buildNShapeOption } from '../chartConfigs/edaCharts';

export function HolidayExpoPage() {
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

  const nShapeOption = useMemo(() => {
    if (!data || !data.n_shape.length) return {};
    return buildNShapeOption(data.n_shape);
  }, [data]);

  const expoOption = useMemo(() => {
    if (!data || !data.expo_effect.day_types.length) return {};
    return buildExpoEffectOption(
      data.expo_effect.day_types,
      data.expo_effect.non_expo,
      data.expo_effect.expo,
    );
  }, [data]);

  if (loading) return <Skeleton active paragraph={{ rows: 8 }} style={{ padding: 24 }} />;
  if (error) return <Result status="error" title={error} extra={<Button type="primary" onClick={refetch}>重试</Button>} />;

  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={4} style={{ marginTop: 0 }}>
        节假日与展会效应
      </Typography.Title>
      <Typography.Paragraph type="secondary">
        节假日期间航空与高铁票价的 N 型效应（节前上涨→假期回落→节末反弹），以及展会日对票价的溢价效应。
      </Typography.Paragraph>

      <Row gutter={[16, 16]}>
        <Col xs={24}>
          {data && data.n_shape.length > 0 ? (
            <Card title="节假日 N 型效应：航空 vs 高铁商务座" styles={{ body: { paddingTop: 8 } }}>
              <Typography.Paragraph type="secondary" style={{ marginBottom: 8, fontSize: 12 }}>
                横轴为相对节假日首日的天数（负数=节前，0=首日，正数=假期中/后），展示航空均价与高铁商务座的 N 型变化。
              </Typography.Paragraph>
              <EchartsBox option={nShapeOption} height={420} />
            </Card>
          ) : (
            <Card title="节假日 N 型效应">
              <Typography.Paragraph type="secondary">当前数据无节假日区间，无法展示 N 型效应。</Typography.Paragraph>
            </Card>
          )}
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} md={12}>
          {data && data.expo_effect.day_types.length > 0 ? (
            <Card title="展会效应：展会日 vs 非展会日" styles={{ body: { paddingTop: 8 } }}>
              <Typography.Paragraph type="secondary" style={{ marginBottom: 8, fontSize: 12 }}>
                对比工作日/非工作日中，展会日与非展会日的平均票价差异。
              </Typography.Paragraph>
              <EchartsBox option={expoOption} height={380} />
            </Card>
          ) : (
            <Card title="展会效应">
              <Typography.Paragraph type="secondary">当前数据无展会日信息，无法展示展会效应。</Typography.Paragraph>
            </Card>
          )}
        </Col>
        <Col xs={24} md={12}>
          <Card title="节假日区间" styles={{ body: { paddingTop: 8 } }}>
            {data && data.holiday_ranges.length > 0 ? (
              <div>
                {data.holiday_ranges.map((hr, i) => (
                  <Typography.Paragraph key={i}>
                    节假日 {i + 1}：{hr.start} 至 {hr.end}
                  </Typography.Paragraph>
                ))}
              </div>
            ) : (
              <Typography.Paragraph type="secondary">无节假日数据</Typography.Paragraph>
            )}
          </Card>
          {data && data.expo_tests.length > 0 && (
            <Card title="展会溢价统计检验" style={{ marginTop: 16 }} styles={{ body: { paddingTop: 8 } }}>
              <Typography.Paragraph type="secondary" style={{ marginBottom: 8, fontSize: 12 }}>
                独立样本 t 检验：对比各日类型下展会日与非展会日的平均票价差异。* 表示 p &lt; 0.05 显著。
              </Typography.Paragraph>
              <Descriptions bordered size="small" column={1}>
                {data.expo_tests.map((t, i) => (
                  <Descriptions.Item key={i} label={t.day_type}>
                    展会日 {t.expo_mean}元 vs 非展会日 {t.non_expo_mean}元，
                    溢价 {t.premium > 0 ? '+' : ''}{t.premium}元，
                    t={t.t_stat}，p={t.p_value}{t.p_value < 0.05 ? ' *' : ''}
                  </Descriptions.Item>
                ))}
              </Descriptions>
            </Card>
          )}
        </Col>
      </Row>
    </div>
  );
}
