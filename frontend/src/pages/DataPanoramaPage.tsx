import { useEffect, useMemo, useRef, useState } from 'react';
import { Alert, Button, Card, Col, Descriptions, Result, Row, Skeleton, Statistic, Typography } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  DatabaseOutlined,
  CalendarOutlined,
  RocketOutlined,
  EnvironmentOutlined,
} from '@ant-design/icons';
import * as echarts from 'echarts';
import { fetchDataPanorama } from '../services/api';
import type { DataPanoramaResponse } from '../types/api';
import {
  dailyRecordsTrendConfig,
  dailyFlightsTrendConfig,
  airlineBarConfig,
  airportPieConfig,
  timeTypePieConfig,
} from '../chartConfigs/panoramaCharts';
import { BG_SECONDARY } from '../constants/colors';

function ChartCard({
  title,
  option,
  height = 300,
}: {
  title: string;
  option: echarts.EChartsOption;
  height?: number;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const chart = echarts.init(el);
    chart.setOption(option, true);
    const ro = new ResizeObserver(() => chart.resize());
    ro.observe(el);
    return () => {
      ro.disconnect();
      chart.dispose();
    };
  }, [option]);

  return (
    <Card title={title} size="small">
      <div ref={containerRef} style={{ width: '100%', height }} />
    </Card>
  );
}

export function DataPanoramaPage() {
  const [data, setData] = useState<DataPanoramaResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchDataPanorama()
      .then((d) => {
        if (!cancelled) {
          setData(d);
          setError(null);
        }
      })
      .catch((e: Error) => {
        if (!cancelled) setError(e.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  const refetch = () => {
    setLoading(true);
    setError(null);
    let cancelled = false;
    fetchDataPanorama()
      .then((d) => {
        if (!cancelled) {
          setData(d);
          setError(null);
        }
      })
      .catch((e: Error) => {
        if (!cancelled) setError(e.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  };

  const dailyRecordsOption = useMemo(() => {
    if (!data) return {};
    return dailyRecordsTrendConfig(
      data.data_quality.daily_records.map((r) => r.date),
      data.data_quality.daily_records.map((r) => r.count),
      data.data_quality.low_coverage_dates,
    );
  }, [data]);

  const dailyFlightsOption = useMemo(() => {
    if (!data) return {};
    return dailyFlightsTrendConfig(
      data.collection_coverage.air.daily_flights.map((r) => r.date),
      data.collection_coverage.air.daily_flights.map((r) => r.count),
    );
  }, [data]);

  const airlineOption = useMemo(() => {
    if (!data) return {};
    const top10 = data.sample_distribution.airlines.slice(0, 10);
    return airlineBarConfig(
      top10.map((a) => a.name),
      top10.map((a) => a.count),
    );
  }, [data]);

  const depAirportOption = useMemo(() => {
    if (!data) return {};
    return airportPieConfig(
      data.sample_distribution.dep_airports.map((a) => a.name),
      data.sample_distribution.dep_airports.map((a) => a.count),
    );
  }, [data]);

  const arrAirportOption = useMemo(() => {
    if (!data) return {};
    return airportPieConfig(
      data.sample_distribution.arr_airports.map((a) => a.name),
      data.sample_distribution.arr_airports.map((a) => a.count),
    );
  }, [data]);

  const timeTypeOption = useMemo(() => {
    if (!data) return {};
    return timeTypePieConfig(
      data.sample_distribution.weekday_count,
      data.sample_distribution.weekend_count,
      data.sample_distribution.holiday_count,
    );
  }, [data]);

  if (loading) {
    return <Skeleton active paragraph={{ rows: 10 }} style={{ padding: 24 }} />;
  }

  if (error || !data) {
    return (
      <Result
        status="error"
        title="数据加载失败"
        subTitle={error ?? '未知错误'}
        extra={<Button type="primary" onClick={refetch}>重试</Button>}
      />
    );
  }

  const dq = data.data_quality;
  const cc = data.collection_coverage;
  const sd = data.sample_distribution;

  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={4} style={{ marginTop: 0 }}>
        数据全景
      </Typography.Title>
      <Typography.Paragraph type="secondary">
        技术数据监控：数据质量、采集覆盖、样本分布。基于原始数据库 air_hsr_pricing.db 实时统计。
      </Typography.Paragraph>

      {/* ====== 数据质量 ====== */}
      <Card
        title={<><CheckCircleOutlined style={{ marginRight: 8, color: '#16A085' }} />数据质量</>}
        style={{ marginBottom: 24 }}
      >
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={6}>
            <Statistic
              title="总记录数"
              value={dq.total_records}
              prefix={<DatabaseOutlined />}
              formatter={(v) => (v as number).toLocaleString('zh-CN')}
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="缺失记录数"
              value={dq.missing_count}
              prefix={dq.missing_count === 0 ? <CheckCircleOutlined style={{ color: '#16A085' }} /> : <CloseCircleOutlined style={{ color: '#C0392B' }} />}
              valueStyle={{ color: dq.missing_count === 0 ? '#16A085' : '#C0392B' }}
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="缺失率"
              value={dq.missing_rate * 100}
              suffix="%"
              precision={2}
              valueStyle={{ color: dq.missing_rate === 0 ? '#16A085' : '#C0392B' }}
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="异常记录数"
              value={dq.anomaly_count}
              prefix={dq.anomaly_count === 0 ? <CheckCircleOutlined style={{ color: '#16A085' }} /> : <WarningOutlined style={{ color: '#F39C12' }} />}
              valueStyle={{ color: dq.anomaly_count === 0 ? '#16A085' : '#F39C12' }}
            />
          </Col>
        </Row>
        {dq.low_coverage_dates.length > 0 && (
          <Alert
            type="warning"
            showIcon
            style={{ marginTop: 16 }}
            message="低覆盖采集日"
            description={`以下日期采集记录数不足中位数的30%：${dq.low_coverage_dates.join('、')}`}
          />
        )}
        <div style={{ marginTop: 16 }}>
          <ChartCard title="每日采集记录数趋势" option={dailyRecordsOption} height={280} />
        </div>
      </Card>

      {/* ====== 采集覆盖 ====== */}
      <Card
        title={<><CalendarOutlined style={{ marginRight: 8, color: '#2980B9' }} />采集覆盖</>}
        style={{ marginBottom: 24 }}
      >
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={6}>
            <Statistic title="航空查询天数" value={cc.air.query_days} suffix="天" prefix={<RocketOutlined />} />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic title="航空出发天数" value={cc.air.dep_days} suffix="天" />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic title="高铁查询天数" value={cc.hsr.query_days} suffix="天" prefix={<RocketOutlined />} />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic title="展会记录数" value={cc.expo.total} suffix="条" prefix={<EnvironmentOutlined />} />
          </Col>
        </Row>
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} md={12}>
            <Descriptions
              bordered
              size="small"
              column={1}
              title="航空数据覆盖"
              styles={{ label: { background: BG_SECONDARY, fontWeight: 600 } }}
            >
              <Descriptions.Item label="查询日期范围">
                {cc.air.query_date_range.start} ~ {cc.air.query_date_range.end}
              </Descriptions.Item>
              <Descriptions.Item label="出发日期范围">
                {cc.air.dep_date_range.start} ~ {cc.air.dep_date_range.end}
              </Descriptions.Item>
              <Descriptions.Item label="唯一航班数">{cc.air.unique_flights}</Descriptions.Item>
            </Descriptions>
          </Col>
          <Col xs={24} md={12}>
            <Descriptions
              bordered
              size="small"
              column={1}
              title="高铁数据覆盖"
              styles={{ label: { background: BG_SECONDARY, fontWeight: 600 } }}
            >
              <Descriptions.Item label="查询日期范围">
                {cc.hsr.query_date_range.start} ~ {cc.hsr.query_date_range.end}
              </Descriptions.Item>
              <Descriptions.Item label="出发日期范围">
                {cc.hsr.dep_date_range.start} ~ {cc.hsr.dep_date_range.end}
              </Descriptions.Item>
              <Descriptions.Item label="聚合记录数">{cc.hsr.total_records}</Descriptions.Item>
            </Descriptions>
          </Col>
        </Row>
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} md={12}>
            <Descriptions
              bordered
              size="small"
              column={1}
              title="展会数据覆盖"
              styles={{ label: { background: BG_SECONDARY, fontWeight: 600 } }}
            >
              <Descriptions.Item label="展会总数">{cc.expo.total}</Descriptions.Item>
              <Descriptions.Item label="日期范围">
                {cc.expo.date_range.start} ~ {cc.expo.date_range.end}
              </Descriptions.Item>
            </Descriptions>
          </Col>
        </Row>
        <div style={{ marginTop: 16 }}>
          <ChartCard title="每日采集航班数趋势" option={dailyFlightsOption} height={280} />
        </div>
      </Card>

      {/* ====== 样本分布 ====== */}
      <Card
        title={<><DatabaseOutlined style={{ marginRight: 8, color: '#8E44AD' }} />样本分布</>}
        style={{ marginBottom: 24 }}
      >
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={4}>
            <Statistic title="最低票价" value={sd.price_stats.min} suffix="元" precision={0} />
          </Col>
          <Col xs={12} sm={4}>
            <Statistic title="最高票价" value={sd.price_stats.max} suffix="元" precision={0} />
          </Col>
          <Col xs={12} sm={4}>
            <Statistic title="均价" value={sd.price_stats.mean} suffix="元" precision={0} />
          </Col>
          <Col xs={12} sm={4}>
            <Statistic title="中位数" value={sd.price_stats.median} suffix="元" precision={0} />
          </Col>
          <Col xs={12} sm={4}>
            <Statistic title="标准差" value={sd.price_stats.std} suffix="元" precision={0} />
          </Col>
          <Col xs={12} sm={4}>
            <Statistic title="航司数" value={sd.airlines.length} suffix="家" />
          </Col>
        </Row>
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} lg={12}>
            <ChartCard title="航司分布（Top 10）" option={airlineOption} height={340} />
          </Col>
          <Col xs={24} lg={12}>
            <Row gutter={[16, 16]}>
              <Col xs={24} md={12}>
                <ChartCard title="起飞机场分布" option={depAirportOption} height={340} />
              </Col>
              <Col xs={24} md={12}>
                <ChartCard title="到达机场分布" option={arrAirportOption} height={340} />
              </Col>
            </Row>
          </Col>
        </Row>
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} md={10}>
            <ChartCard title="时间类型分布（工作日/周末/节假日）" option={timeTypeOption} height={320} />
          </Col>
          <Col xs={24} md={14}>
            <Descriptions
              bordered
              size="small"
              column={2}
              title="样本构成明细"
              styles={{ label: { background: BG_SECONDARY, fontWeight: 600 } }}
            >
              <Descriptions.Item label="工作日记录">{sd.normal_count.toLocaleString('zh-CN')}</Descriptions.Item>
              <Descriptions.Item label="节假日记录">{sd.holiday_count.toLocaleString('zh-CN')}</Descriptions.Item>
              <Descriptions.Item label="工作日记录">{sd.weekday_count.toLocaleString('zh-CN')}</Descriptions.Item>
              <Descriptions.Item label="周末记录">{sd.weekend_count.toLocaleString('zh-CN')}</Descriptions.Item>
              <Descriptions.Item label="节假日占比">
                {((sd.holiday_count / dq.total_records) * 100).toFixed(2)}%
              </Descriptions.Item>
              <Descriptions.Item label="周末占比">
                {((sd.weekend_count / dq.total_records) * 100).toFixed(2)}%
              </Descriptions.Item>
            </Descriptions>
          </Col>
        </Row>
      </Card>
    </div>
  );
}
