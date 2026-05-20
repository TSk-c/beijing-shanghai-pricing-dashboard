import { useEffect, useState } from 'react';
import { Card, Col, Row, Skeleton, Typography } from 'antd';
import { AirHsrPriceComparisonChart } from '../components/AirHsrPriceComparisonChart';
import { KpiCard } from '../components/KpiCard';
import { fetchOverview, fetchRpaTrend } from '../services/api';
import { mockRpaTrend } from '../services/mockData';
import { useDashboardStore } from '../store/dashboardStore';
import type { OverviewResponse } from '../types/overview';
import type { AirHsrPriceComparisonInput } from '../types/charts';

function formatOverviewKpis(overview: OverviewResponse) {
  const total = overview.total_records;
  const hsrPct = overview.hsr_coverage * 100;
  const span = `${overview.date_range.start} 至 ${overview.date_range.end}`;
  const mape = overview.best_model_mape;
  return { total, hsrPct, span, mape };
}

function toAirHsrInput(trend: Awaited<ReturnType<typeof fetchRpaTrend>>): AirHsrPriceComparisonInput {
  return {
    dates: trend.dates,
    airPrices: trend.airPrices,
    hsrSecond: trend.hsrSecond,
    hsrFirst: trend.hsrFirst,
    hsrBusiness: trend.hsrBusiness,
    weekends: trend.weekends,
    holidays: trend.holidays,
  };
}

export function HomePage() {
  const data = useDashboardStore((s) => s.data);
  const setData = useDashboardStore((s) => s.setData);
  const setError = useDashboardStore((s) => s.setError);
  const [trendInput, setTrendInput] = useState<AirHsrPriceComparisonInput>(() => ({
    dates: [...mockRpaTrend.dates],
    airPrices: [...mockRpaTrend.airPrices],
    hsrSecond: [...mockRpaTrend.hsrSecond],
    hsrFirst: [...mockRpaTrend.hsrFirst],
    hsrBusiness: [...mockRpaTrend.hsrBusiness],
    weekends: [...mockRpaTrend.weekends],
    holidays: { ...mockRpaTrend.holidays },
  }));

  useEffect(() => {
    let cancelled = false;
    setError(null);
    void fetchOverview().then((overview) => {
      if (!cancelled) {
        setData(overview);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [setData, setError]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const trend = await fetchRpaTrend();
      if (!cancelled) {
        setTrendInput(toAirHsrInput(trend));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const kpis = data ? formatOverviewKpis(data) : null;

  return (
    <div style={{ padding: 24 }}>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <KpiCard
            title="总航班记录数"
            targetNumber={kpis?.total}
            formatAnimated={(n) => Math.round(n).toLocaleString('zh-CN')}
            footer="全样本航班记录条数"
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <KpiCard
            title="高铁有效匹配率"
            targetNumber={kpis?.hsrPct}
            formatAnimated={(n) => `${n.toFixed(0)}%`}
            footer="与高铁票价成功匹配的比例"
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <KpiCard
            title="数据时间跨度"
            valueText={kpis?.span ?? '—'}
            footer="样本覆盖的起止日期"
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <KpiCard
            title="最优模型MAPE"
            targetNumber={kpis?.mape}
            formatAnimated={(n) => `${n.toFixed(2)}%`}
            footer="当前最优模型为 XGBoost"
          />
        </Col>
      </Row>
      <Card
        title="核心趋势：航空与高铁各等级票价时间序列对比"
        style={{ marginTop: 24 }}
        styles={{ body: { paddingTop: 8 } }}
      >
        <Typography.Paragraph type="secondary" style={{ marginBottom: 12 }}>
          黑线为航空日均价（左轴），虚线为高铁二等座/一等座/商务座（右轴）；浅蓝/浅橙区域分别为周末与节假日示意。
        </Typography.Paragraph>
        {!data ? (
          <Skeleton active paragraph={{ rows: 6 }} />
        ) : (
          <AirHsrPriceComparisonChart data={trendInput} height={440} />
        )}
      </Card>
    </div>
  );
}
