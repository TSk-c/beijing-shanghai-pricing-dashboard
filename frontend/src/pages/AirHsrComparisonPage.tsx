import { useEffect, useMemo, useState } from 'react';
import { Button, Card, Result, Skeleton, Typography } from 'antd';
import { EchartsBox } from '../components/EchartsBox';
import { fetchEdaCharts, fetchRpaTrend } from '../services/api';
import type { EdaChartsResponse, RpaTrendResponse } from '../types/api';
import { buildRemainTrendOption, buildSupplyEffectOption, buildSupplyTrendOption } from '../chartConfigs/edaCharts';
import { airHsrPriceComparisonConfig } from '../chartConfigs/airHsrPriceComparison';
import type { AirHsrPriceComparisonInput } from '../types/charts';

export function AirHsrComparisonPage() {
  const [edaData, setEdaData] = useState<EdaChartsResponse | null>(null);
  const [trendData, setTrendData] = useState<RpaTrendResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [eda, trend] = await Promise.all([fetchEdaCharts(), fetchRpaTrend()]);
        if (!cancelled) {
          setEdaData(eda);
          setTrendData(trend);
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
          setTrendData(trend);
        }
      } catch {
        if (!cancelled) setError('数据加载失败');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  };

  const priceCompOption = useMemo(() => {
    if (!trendData) return {};
    const input: AirHsrPriceComparisonInput = {
      dates: trendData.dates,
      airPrices: trendData.airPrices,
      hsrSecond: trendData.hsrSecond,
      hsrFirst: trendData.hsrFirst,
      hsrBusiness: trendData.hsrBusiness,
      weekends: trendData.weekends,
      holidays: trendData.holidays,
    };
    return airHsrPriceComparisonConfig(input);
  }, [trendData]);

  const remainOption = useMemo(() => {
    if (!edaData) return {};
    return buildRemainTrendOption(
      edaData.remain_trend.dates,
      edaData.remain_trend.air_avg,
      edaData.remain_trend.remain_C,
      edaData.remain_trend.remain_F,
      edaData.remain_trend.remain_S,
      edaData.remain_trend.weekends,
      edaData.remain_trend.holidays,
    );
  }, [edaData]);

  const supplyEffectOption = useMemo(() => {
    if (!edaData || !edaData.supply_effect.scatter.length) return {};
    return buildSupplyEffectOption(edaData.supply_effect.scatter);
  }, [edaData]);

  const supplyTrendOption = useMemo(() => {
    if (!edaData || !edaData.supply_trend.dates.length) return {};
    return buildSupplyTrendOption(
      edaData.supply_trend.dates,
      edaData.supply_trend.air_avg,
      edaData.supply_trend.supply_avg,
      edaData.supply_trend.pearson_r,
      edaData.supply_trend.pearson_p,
      edaData.supply_trend.weekends,
      edaData.supply_trend.holidays,
    );
  }, [edaData]);

  if (loading) return <Skeleton active paragraph={{ rows: 8 }} style={{ padding: 24 }} />;
  if (error) return <Result status="error" title={error} extra={<Button type="primary" onClick={refetch}>重试</Button>} />;

  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={4} style={{ marginTop: 0 }}>
        空铁价格与余票对比
      </Typography.Title>
      <Typography.Paragraph type="secondary">
        航空与高铁各等级票价时间序列对比、高铁余票变化趋势、供给紧张度与航空票价走势。
      </Typography.Paragraph>

      <Card title="航空与高铁各等级票价时间序列对比" styles={{ body: { paddingTop: 8 } }}>
        <Typography.Paragraph type="secondary" style={{ marginBottom: 8, fontSize: 12 }}>
          黑线为航空日均价（左轴），虚线为高铁二等座/一等座/商务座（右轴）；浅蓝/浅橙区域为周末与节假日。
        </Typography.Paragraph>
        <EchartsBox option={priceCompOption} height={440} />
      </Card>

      <Card title="高铁余票时序" style={{ marginTop: 16 }} styles={{ body: { paddingTop: 8 } }}>
        <Typography.Paragraph type="secondary" style={{ marginBottom: 8, fontSize: 12 }}>
          左轴为航空日均价（参考），右轴为高铁各等级余票数量；浅蓝/浅橙区域为周末与节假日。
        </Typography.Paragraph>
        <EchartsBox option={remainOption} height={440} />
      </Card>

      {edaData && edaData.supply_effect.scatter.length > 0 && (
        <Card title="供给紧张度对航空票价的影响：节假日 vs 工作日" style={{ marginTop: 16 }} styles={{ body: { paddingTop: 8 } }}>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 8, fontSize: 12 }}>
            散点图展示高铁供给紧张度与航空票价的关系，蓝色为工作日，红色为节假日；虚线为线性回归拟合。
          </Typography.Paragraph>
          <EchartsBox option={supplyEffectOption} height={420} />
        </Card>
      )}

      {edaData && edaData.supply_trend.dates.length > 0 && (
        <Card title="供给紧张度与航空票价走势" style={{ marginTop: 16 }} styles={{ body: { paddingTop: 8 } }}>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 8, fontSize: 12 }}>
            高铁供给紧张度（同提前期标准化）与航空日均价的双轴对比，含 Pearson 相关系数。
          </Typography.Paragraph>
          <EchartsBox option={supplyTrendOption} height={440} />
        </Card>
      )}
    </div>
  );
}
