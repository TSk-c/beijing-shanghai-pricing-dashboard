import { useEffect, useState } from 'react';
import { Card, Typography } from 'antd';
import { RpaCorrelationChart } from '../components/RpaCorrelationChart';
import { fetchRpaTrend } from '../services/api';
import { mockRpaTrend } from '../services/mockData';
import type { DualAxisTimeSeriesInput } from '../types/charts';

const fallbackTrend: DualAxisTimeSeriesInput = {
  dates: [...mockRpaTrend.dates],
  airPrices: [...mockRpaTrend.airPrices],
  rpaValues: [...mockRpaTrend.rpaValues],
  weekends: [...mockRpaTrend.weekends],
  holidays: { ...mockRpaTrend.holidays },
  pearsonR: mockRpaTrend.pearson_r,
  pearsonP: mockRpaTrend.pearson_p,
};

export function RpaTrendPage() {
  const [trendData, setTrendData] = useState<DualAxisTimeSeriesInput>(fallbackTrend);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const d = await fetchRpaTrend();
      if (!cancelled) {
        setTrendData({
          dates: [...d.dates],
          airPrices: [...d.airPrices],
          rpaValues: [...d.rpaValues],
          weekends: [...d.weekends],
          holidays: d.holidays ? { ...d.holidays } : undefined,
          pearsonR: d.pearson_r ?? null,
          pearsonP: d.pearson_p ?? null,
        });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const pearsonText =
    trendData.pearsonR != null && trendData.pearsonP != null
      ? `Pearson r = ${trendData.pearsonR.toFixed(3)}, p = ${trendData.pearsonP.toFixed(4)}`
      : null;

  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={4} style={{ marginTop: 0 }}>
        高铁相对价格优势 (RPA) 与航空票价走势
      </Typography.Title>
      <Typography.Paragraph type="secondary">
        黑线为航空日均价（左轴），蓝虚线为 RPA（右轴）；浅蓝/浅橙区域分别为周末与节假日示意。
        {pearsonText && (
          <>
            <br />
            相关性：{pearsonText}
          </>
        )}
      </Typography.Paragraph>
      <Card>
        <RpaCorrelationChart data={trendData} height={480} />
      </Card>
    </div>
  );
}
