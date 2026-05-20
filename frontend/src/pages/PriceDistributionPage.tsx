import { useEffect, useState } from 'react';
import { Card, Col, Row, Statistic, Typography } from 'antd';
import { PriceDistributionChart } from '../components/PriceDistributionChart';
import { fetchPriceDistribution } from '../services/api';
import { mockPriceDistribution } from '../services/mockData';
import type { PriceDistributionInput } from '../types/priceDistribution';

const fallbackDist: PriceDistributionInput = {
  bins: mockPriceDistribution.bins.map((b) => ({ ...b })),
  median: mockPriceDistribution.median,
  mean: mockPriceDistribution.mean,
  skewness: mockPriceDistribution.skewness,
  kurtosis: mockPriceDistribution.kurtosis,
};

export function PriceDistributionPage() {
  const [distData, setDistData] = useState<PriceDistributionInput>(fallbackDist);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const d = await fetchPriceDistribution();
      if (!cancelled) {
        setDistData({
          bins: d.bins.map((b) => ({ ...b })),
          median: d.median,
          mean: d.mean,
          skewness: d.skewness,
          kurtosis: d.kurtosis,
        });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={4} style={{ marginTop: 0 }}>
        票价分布
      </Typography.Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card title="票价直方图与核密度（KDE）">
            <PriceDistributionChart data={distData} height={440} />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="分布形态统计">
            <Statistic title="偏度（Skewness）" value={distData.skewness} precision={2} />
            <Statistic
              title="峰度（Kurtosis）"
              value={distData.kurtosis}
              precision={2}
              style={{ marginTop: 24 }}
            />
            <Typography.Paragraph type="secondary" style={{ marginTop: 24, marginBottom: 0 }}>
              中位数 {distData.median} 元，均值 {distData.mean} 元；图中蓝虚线为
              中位数，黑虚线为均值；红线为 KDE 曲线。数据来自 /api/price/distribution。
            </Typography.Paragraph>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
