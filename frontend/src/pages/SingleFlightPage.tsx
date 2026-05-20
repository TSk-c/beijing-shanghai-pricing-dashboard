import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Col,
  Collapse,
  Form,
  Input,
  InputNumber,
  Row,
  Select,
  Skeleton,
  Space,
  Table,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import {
  BG_PRIMARY,
  BG_SECONDARY,
  INFO,
  SECONDARY,
  SHAP_HIGH,
  SHAP_LOW,
  STATUS_DOWN,
  STATUS_HOLD,
  STATUS_UP,
  SUCCESS,
  TEXT_MUTED,
  TEXT_PRIMARY,
  TEXT_SECONDARY,
  WARNING,
} from '../constants/colors';
import { buildCategoryContributionOption, buildShapWaterfallOption, CATEGORY_COLORS } from '../chartConfigs/attributionCharts';
import { EchartsBox } from '../components/EchartsBox';
import {
  fetchFlights,
  fetchFlightsByDate,
  fetchPredictionCoverage,
  postModelPredictFlight,
  postModelPredictFlightPrices,
  type FlightInfo,
  type PredictFlightPricesResponse,
  type PredictionCoverageResponse,
} from '../services/api';
import { mockPredictResult } from '../services/mockData';
import type { CategorySummary, PredictResponse } from '../types/api';

type StrategyTone = 'up' | 'down' | 'hold';

function resolveStrategyTone(text: string): StrategyTone {
  if (text.includes('上调')) return 'up';
  if (text.includes('下调')) return 'down';
  return 'hold';
}

const CATEGORY_TAG_COLORS: Record<string, string> = CATEGORY_COLORS;

const FEATURE_LABELS: Record<string, string> = {
  days_prior: '提前天数',
  days_prior_sq: '提前天数²',
  dep_dow: '出发星期',
  dep_time_hour: '出发时段',
  dep_period_enc: '时段编码',
  is_weekend: '是否周末',
  is_pre_holiday_peak: '节前高峰',
  is_pre_holiday_buildup: '节前积蓄',
  holiday_day_num: '假期天数',
  is_holiday_mid: '假期中段',
  is_holiday_last_2d: '假期末尾',
  is_post_holiday_dip: '节后回落',
  days_to_nearest_holiday: '距最近假日',
  expo_max_scale: '展会规模',
  is_expo_day: '是否展会日',
  airline_enc: '航司编码',
  dep_airport_enc: '出发机场',
  arr_airport_enc: '到达机场',
  duration_hours: '飞行时长',
  hsr_data_available: '高铁可售',
  rpa_F: 'RPA指数',
  price_diff_F: '价差',
  supply_tension_F: '供给紧张度',
  rpa_F_x_days_prior: 'RPA×提前天数',
  supply_tension_F_x_is_holiday: '紧张度×假日',
  supply_tension_F_x_is_weekend: '紧张度×周末',
  price_diff_F_x_days_prior: '价差×提前天数',
  rpa_F_x_is_weekend: 'RPA×周末',
  rpa_F_high: 'RPA高',
  rpa_F_low: 'RPA低',
  supply_tension_high: '供给紧张高',
  price_F: '高铁一等座价',
  remain_F: '一等座余票',
  price_C: '高铁二等座价',
  remain_C: '二等座余票',
  price_S: '商务座价',
  remain_S: '商务座余票',
  hsr_avg_duration_h: '高铁时长',
  train_count: '车次数',
  hsr_F_S_spread: '一二等价差',
  hsr_total_remain: '总余票',
};

function featLabel(f: string): string {
  return FEATURE_LABELS[f] ?? f;
}

function generateInterpretation(
  baseValue: number,
  predictedPrice: number,
  categorySummary: Record<string, CategorySummary>,
  status: PredictResponse['competitive_status'],
): string {
  const sorted = Object.entries(categorySummary)
    .sort(([, a], [, b]) => b.total_abs_contribution - a.total_abs_contribution);
  const dominant = sorted[0];
  const parts: string[] = [];

  parts.push(
    `模型基准价 ¥${baseValue.toFixed(0)}，经各因素调整后预测 ¥${predictedPrice.toFixed(0)}。`,
  );

  if (dominant) {
    const [cat, info] = dominant;
    const dir = info.net_contribution >= 0 ? '推高' : '压低';
    parts.push(
      `定价最大驱动力来自「${cat}」（绝对贡献 ¥${info.total_abs_contribution.toFixed(0)}，净${dir} ¥${Math.abs(info.net_contribution).toFixed(0)}），` +
      `其中 ${info.top_features.map((t) => `${featLabel(t.feature)}（${t.shap_value >= 0 ? '+' : ''}${t.shap_value.toFixed(0)}）`).join('、')} 贡献最大。`,
    );
  }

  const expoCat = categorySummary['展会冲击'];
  if (expoCat) {
    if (expoCat.total_abs_contribution > 5) {
      parts.push(`展会因素产生显著影响（净贡献 ¥${expoCat.net_contribution.toFixed(0)}），验证了外生商务需求冲击对定价的调节作用。`);
    } else {
      parts.push(`展会因素影响较小（绝对贡献 ¥${expoCat.total_abs_contribution.toFixed(0)}），该航班定价未受展会活动显著驱动。`);
    }
  }

  const hsrCat = categorySummary['高铁竞争'];
  if (hsrCat) {
    if (Math.abs(hsrCat.net_contribution) > 10) {
      const dir = hsrCat.net_contribution < 0 ? '压低' : '推高';
      parts.push(`高铁竞争因素显著${dir}定价（净贡献 ¥${Math.abs(hsrCat.net_contribution).toFixed(0)}），体现了空铁竞争对航空定价的约束效应。`);
    } else {
      parts.push(`高铁竞争因素影响有限（净贡献 ¥${hsrCat.net_contribution.toFixed(0)}），该场景下航司定价相对独立。`);
    }
  }

  if (status) {
    parts.push(`当前 RPA 态势为「${status.rpa_level}」，供给状态「${status.supply_status}」，建议「${status.recommendation}」。`);
  }

  return parts.join('');
}

function buildPriceCurveOption(
  prices: PredictFlightPricesResponse['prices'],
  bestDaysPrior: number,
) {
  const sorted = [...prices].sort((a, b) => a.days_prior - b.days_prior);
  return {
    tooltip: {
      trigger: 'axis' as const,
      backgroundColor: 'rgba(255,255,255,0.96)',
      borderColor: '#E0E0E0',
      textStyle: { color: TEXT_PRIMARY, fontSize: 12 },
      formatter: (p: unknown) => {
        const params = (p as { name?: string; value?: number; dataIndex?: number }[])[0];
        if (!params) return '';
        const dp = sorted[params.dataIndex ?? 0];
        if (!dp) return '';
        const isBest = dp.days_prior === bestDaysPrior;
        const expiredTag = dp.is_expired ? ` <span style="color:${TEXT_MUTED};font-size:10px">[已过期]</span>` : '';
        return `提前 ${params.name} 天<br/>预测价格：¥${params.value?.toFixed(1)}${expiredTag}${isBest ? `<br/><b style="color:${SECONDARY}">★ 最优购买时机</b>` : ''}`;
      },
    },
    grid: { top: 40, right: 40, bottom: 40, left: 64 },
    xAxis: {
      type: 'category' as const,
      data: sorted.map((p) => {
        const label = String(p.days_prior);
        return p.is_expired ? `${label}(过期)` : label;
      }),
      axisLabel: {
        color: TEXT_SECONDARY,
        fontSize: 11,
        formatter: (v: string) => (v.includes('(过期)') ? v : v),
      },
      name: '提前天数',
      nameTextStyle: { color: TEXT_SECONDARY, fontSize: 10 },
      axisLine: { lineStyle: { color: '#E0E0E0' } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value' as const,
      name: '预测价格（元）',
      nameTextStyle: { color: TEXT_SECONDARY, fontSize: 11 },
      splitLine: { lineStyle: { type: 'dashed' as const, color: '#E8E8E8' } },
      axisLabel: { color: TEXT_SECONDARY, fontSize: 11 },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: [{
      type: 'line' as const,
      data: sorted.map((p) => ({
        value: p.predicted_price,
        itemStyle: {
          color: p.is_expired ? SECONDARY : (p.days_prior === bestDaysPrior ? SUCCESS : INFO),
          borderColor: p.is_expired ? SECONDARY : undefined,
          borderWidth: p.is_expired ? 1 : 0,
        },
      })),
      smooth: true,
      symbolSize: (_val: unknown, params: { dataIndex: number }) => {
        const dp = sorted[params.dataIndex];
        if (dp?.days_prior === bestDaysPrior) return 12;
        if (dp?.is_expired) return 4;
        return 6;
      },
      lineStyle: {
        color: INFO,
        width: 2,
        type: 'solid' as const,
      },
    }],
    backgroundColor: BG_PRIMARY,
  };
}

export function SingleFlightPage() {
  const [form] = Form.useForm<{ flightNo: string; depDate: string; daysPrior: number }>();
  const [submitted, setSubmitted] = useState(false);
  const [predictLoading, setPredictLoading] = useState(false);
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [pricesResult, setPricesResult] = useState<PredictFlightPricesResponse | null>(null);
  const [flights, setFlights] = useState<FlightInfo[]>([]);
  const [flightsLoading, setFlightsLoading] = useState(true);
  const [dateFlights, setDateFlights] = useState<string[]>([]);
  const [dateFlightsLoading, setDateFlightsLoading] = useState(false);
  const [predictError, setPredictError] = useState<{ message: string; availableFlights: string[]; hasFlightOnDate: boolean } | null>(null);
  const [coverage, setCoverage] = useState<PredictionCoverageResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchFlights();
        if (!cancelled) setFlights(data);
      } catch {
        if (!cancelled) setFlights([]);
      } finally {
        if (!cancelled) setFlightsLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchPredictionCoverage();
        if (!cancelled) setCoverage(data);
      } catch {
        if (!cancelled) setCoverage(null);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const depDate = Form.useWatch('depDate', form);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      if (!depDate) {
        if (!cancelled) {
          setDateFlights([]);
          setDateFlightsLoading(false);
        }
        return;
      }
      if (!cancelled) setDateFlightsLoading(true);
      try {
        const res = await fetchFlightsByDate(depDate);
        if (!cancelled) setDateFlights(res.flights);
      } catch {
        if (!cancelled) setDateFlights([]);
      } finally {
        if (!cancelled) setDateFlightsLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [depDate]);

  const flightOptions = useMemo(() => {
    if (!depDate || dateFlights.length === 0) {
      return flights.map((f) => ({
        label: `${f.flight_no}  ${f.airline}  ${f.dep_airport}→${f.arr_airport}  ${f.dep_time}-${f.arr_time}`,
        value: f.flight_no,
      }));
    }
    const availableSet = new Set(dateFlights);
    return flights
      .filter((f) => availableSet.has(f.flight_no))
      .map((f) => ({
        label: `${f.flight_no}  ${f.airline}  ${f.dep_airport}→${f.arr_airport}  ${f.dep_time}-${f.arr_time}`,
        value: f.flight_no,
      }));
  }, [flights, dateFlights, depDate]);

  const tone = useMemo(() => {
    const rec = result?.competitive_status?.recommendation ?? mockPredictResult.competitive_status.recommendation;
    return resolveStrategyTone(rec);
  }, [result]);

  const strategyCardStyle = useMemo(() => {
    if (tone === 'up') return { borderColor: STATUS_UP, background: 'rgba(192, 57, 43, 0.06)' };
    if (tone === 'down') return { borderColor: STATUS_DOWN, background: 'rgba(22, 160, 133, 0.08)' };
    return { borderColor: STATUS_HOLD, background: 'rgba(243, 156, 18, 0.08)' };
  }, [tone]);

  const extractErrorDetail = (err: unknown): { message: string; availableFlights: string[]; hasFlightOnDate: boolean } | null => {
    const axiosErr = err as { response?: { data?: { detail?: unknown }; status?: number }; message?: string; code?: string };
    const detail = axiosErr?.response?.data?.detail;

    if (detail && typeof detail === 'object' && detail !== null) {
      const d = detail as { message?: string; available_flights?: string[]; has_flight_on_date?: boolean };
      return {
        message: d.message ?? String(detail),
        availableFlights: d.available_flights ?? [],
        hasFlightOnDate: d.has_flight_on_date ?? false,
      };
    }

    if (typeof detail === 'string' && detail.length > 0) {
      return {
        message: detail,
        availableFlights: [],
        hasFlightOnDate: false,
      };
    }

    const status = axiosErr?.response?.status;
    if (status === 503) {
      return {
        message: '模型服务暂不可用，请等待模型加载完成后重试',
        availableFlights: [],
        hasFlightOnDate: false,
      };
    }

    console.error('Predict error:', axiosErr?.message ?? err, axiosErr?.code, axiosErr?.response?.status);
    return null;
  };

  const onFinish = async () => {
    const values = await form.validateFields();
    setPredictLoading(true);
    setPredictError(null);
    setResult(null);
    setPricesResult(null);

    const [predictOutcome, pricesOutcome] = await Promise.allSettled([
      postModelPredictFlight(values.flightNo, values.depDate, values.daysPrior),
      postModelPredictFlightPrices(values.flightNo, values.depDate),
    ]);

    const predictErr = predictOutcome.status === 'rejected' ? extractErrorDetail(predictOutcome.reason) : null;
    const pricesErr = pricesOutcome.status === 'rejected' ? extractErrorDetail(pricesOutcome.reason) : null;

    const anyRejected = predictOutcome.status === 'rejected' || pricesOutcome.status === 'rejected';

    if (anyRejected) {
      const bestErr = pricesErr ?? predictErr;
      setPredictError({
        message: bestErr?.message ?? '预测请求失败，请检查网络或稍后重试',
        availableFlights: bestErr?.availableFlights ?? [],
        hasFlightOnDate: bestErr?.hasFlightOnDate ?? false,
      });
      if (predictOutcome.status === 'fulfilled') setResult(predictOutcome.value);
      if (pricesOutcome.status === 'fulfilled') setPricesResult(pricesOutcome.value);
      setSubmitted(true);
    } else {
      setResult(predictOutcome.value);
      setPricesResult(pricesOutcome.value);
      setSubmitted(true);
    }

    setPredictLoading(false);
  };

  const display = result;
  const baseValue = display?.base_value ?? 800;
  const status = display?.competitive_status ?? mockPredictResult.competitive_status;
  const shapDetail = display?.shap_detail;
  const drivers = display?.key_drivers ?? mockPredictResult.key_drivers;

  const waterfallOption = useMemo(() => {
    if (!shapDetail?.waterfall.length) return {};
    return buildShapWaterfallOption(shapDetail.waterfall);
  }, [shapDetail]);

  const categoryOption = useMemo(() => {
    if (!shapDetail?.category_summary) return {};
    return buildCategoryContributionOption(shapDetail.category_summary);
  }, [shapDetail]);

  const interpretation = useMemo(() => {
    if (!display?.shap_detail?.category_summary) return '';
    return generateInterpretation(baseValue, display.predicted_price, display.shap_detail.category_summary, display.competitive_status);
  }, [display, baseValue]);

  const priceCurveOption = useMemo(() => {
    if (!pricesResult) return {};
    return buildPriceCurveOption(pricesResult.prices, pricesResult.best_buy.days_prior);
  }, [pricesResult]);

  const priceTableColumns = useMemo(() => [
    {
      title: '提前天数',
      dataIndex: 'days_prior',
      key: 'days_prior',
      render: (v: number) => `${v} 天`,
    },
    {
      title: '购票日期',
      dataIndex: 'purchase_date',
      key: 'purchase_date',
      render: (v: string) => v,
    },
    {
      title: '预测价格',
      dataIndex: 'predicted_price',
      key: 'predicted_price',
      render: (v: number, record: PredictFlightPricesResponse['prices'][0]) => {
        const isBest = pricesResult?.best_buy.days_prior === record.days_prior;
        return (
          <span style={{ fontWeight: isBest ? 700 : 400, color: record.is_expired ? TEXT_MUTED : (isBest ? SECONDARY : TEXT_PRIMARY) }}>
            ¥{v.toFixed(1)}
            {isBest && <Tag color="red" style={{ marginLeft: 6, fontSize: 10 }}>最低</Tag>}
          </span>
        );
      },
    },
    {
      title: '状态',
      dataIndex: 'is_expired',
      key: 'is_expired',
      render: (v: boolean) => v ? <Tag color="default">已过期</Tag> : <Tag color="green">可操作</Tag>,
    },
  ], [pricesResult]);

  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={4} style={{ marginTop: 0 }}>
        定价规则解读
      </Typography.Title>
      <Typography.Paragraph type="secondary" style={{ marginTop: -8, marginBottom: 16 }}>
        选择航班与出发日期，预测不同提前天数下的购票价格，找出最优购买时机。同时通过 SHAP 归因分析逆向解读航司定价逻辑。
      </Typography.Paragraph>

      {coverage && (
        <Collapse
          size="small"
          style={{ marginBottom: 16 }}
          items={[{
            key: 'coverage',
            label: <span style={{ fontSize: 13, color: TEXT_SECONDARY }}>📊 数据覆盖范围与预测方法说明</span>,
            children: (
              <div style={{ fontSize: 12, color: TEXT_SECONDARY, lineHeight: 2 }}>
                <Row gutter={[16, 8]}>
                  <Col span={8}>
                    <div>爬取日期：{coverage.query_date_range.min} ~ {coverage.query_date_range.max}</div>
                  </Col>
                  <Col span={8}>
                    <div>出发日期：{coverage.dep_date_range.min} ~ {coverage.dep_date_range.max}</div>
                  </Col>
                  <Col span={8}>
                    <div>提前天数：{coverage.days_prior_range.min} ~ {coverage.days_prior_range.max} 天</div>
                  </Col>
                </Row>
                <Row gutter={[16, 8]}>
                  <Col span={8}>
                    <div>航班数量：{coverage.flight_count} 个</div>
                  </Col>
                  <Col span={8}>
                    <div>数据总行数：{coverage.total_rows.toLocaleString()}</div>
                  </Col>
                </Row>
                <div style={{ marginTop: 8, padding: '8px 12px', background: 'rgba(52,152,219,0.06)', borderRadius: 6 }}>
                  <strong style={{ color: TEXT_PRIMARY }}>预测方法：</strong>{coverage.method}
                  <br />
                  {coverage.note}
                </div>
              </div>
            ),
          }]}
        />
      )}

      <Row gutter={[24, 16]}>
        <Col xs={24} lg={12}>
          <Card title="查询条件" size="small">
            {flightsLoading ? (
              <Skeleton active paragraph={{ rows: 4 }} />
            ) : (
              <Form
                form={form}
                layout="vertical"
                onFinish={onFinish}
                initialValues={{
                  flightNo: undefined,
                  depDate: '2026-05-20',
                  daysPrior: 7,
                }}
              >
                <Form.Item name="depDate" label="出发日期" rules={[{ required: true, message: '请选择出发日期' }]}>
                  <Input type="date" />
                </Form.Item>
                <Form.Item name="flightNo" label="航班号" rules={[{ required: true, message: '请选择航班号' }]}>
                  <Select
                    options={flightOptions}
                    placeholder={dateFlightsLoading ? '加载中...' : (depDate ? `当天 ${dateFlights.length} 个航班可选` : '请选择航班')}
                    allowClear
                    showSearch
                    disabled={dateFlightsLoading}
                    filterOption={(input, option) =>
                      (option?.label as string)?.toLowerCase().includes(input.toLowerCase()) ?? false
                    }
                  />
                </Form.Item>
                <Form.Item name="daysPrior" label="SHAP解读提前天数" rules={[{ required: true, message: '请输入提前天数' }]}
                  extra="用于SHAP归因分析的提前天数，价格曲线会自动覆盖多个提前天数"
                >
                  <InputNumber min={0} max={120} style={{ width: '100%' }} />
                </Form.Item>
                <Form.Item>
                  <Button type="primary" htmlType="submit" loading={predictLoading} block>
                    预测价格
                  </Button>
                </Form.Item>
              </Form>
            )}
          </Card>

          {submitted && predictError && (
            <Alert
              type="warning"
              showIcon
              style={{ marginTop: 16 }}
              message={predictError.message}
              description={
                <div>
                  {predictError.hasFlightOnDate ? (
                    <Typography.Text>该航班在当天有数据，但可能没有对应提前天数的记录。</Typography.Text>
                  ) : (
                    <>
                      <Typography.Text>当天可用航班：</Typography.Text>
                      <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                        {predictError.availableFlights.map((f) => (
                          <Tag key={f} color="blue" style={{ cursor: 'pointer' }} onClick={() => form.setFieldsValue({ flightNo: f })}>
                            {f}
                          </Tag>
                        ))}
                      </div>
                    </>
                  )}
                </div>
              }
            />
          )}
        </Col>

        <Col xs={24} lg={12}>
          {submitted && display ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <Card title="预测结果" size="small">
                <Typography.Title level={2} style={{ margin: 0, color: TEXT_PRIMARY }}>
                  ¥{display.predicted_price.toFixed(1)}
                </Typography.Title>
                <Typography.Paragraph type="secondary" style={{ marginTop: 4, marginBottom: 0, fontSize: 12 }}>
                  基准价 ¥{baseValue.toFixed(0)} → 预测价 ¥{display.predicted_price.toFixed(0)}
                  （偏移 ¥{(display.predicted_price - baseValue).toFixed(0)}）
                </Typography.Paragraph>
                <div style={{ marginTop: 12 }}>
                  <Tooltip title="模型对平均预测价格的把握：如果有100个条件相同的航班，它们的平均价格有95%概率在这个区间内。反映模型精度。">
                    <Typography.Text style={{ fontSize: 14, color: TEXT_PRIMARY, fontWeight: 500, cursor: 'help', borderBottom: '1px dashed #95A5A6' }}>
                      置信区间：{display.confidence_interval[0].toFixed(0)} — {display.confidence_interval[1].toFixed(0)} 元
                    </Typography.Text>
                  </Tooltip>
                </div>
                {display.prediction_interval_95 && (
                  <div style={{ marginTop: 4 }}>
                    <Tooltip title="单个航班实际价格的可能范围：该航班实际售价有95%概率落在这个区间内。区间较宽是因为单次价格波动远大于均值。">
                      <Typography.Text type="secondary" style={{ fontSize: 11, cursor: 'help' }}>
                        参考：实际价格约 {display.prediction_interval_95[0].toFixed(0)} — {display.prediction_interval_95[1].toFixed(0)} 元
                      </Typography.Text>
                    </Tooltip>
                  </div>
                )}
              </Card>

              {pricesResult && pricesResult.reference_price != null && (
                <Card title="参考价格（历史记录）" size="small">
                  <Typography.Title level={3} style={{ margin: 0, color: TEXT_PRIMARY }}>
                    ¥{pricesResult.reference_price}
                  </Typography.Title>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    最近一次爬取的该航班实际票价，仅供参考
                  </Typography.Text>
                </Card>
              )}

              {pricesResult && (
                <Card
                  title={`最优购买建议（距出发${pricesResult.remaining_days}天）`}
                  size="small"
                  style={{ borderWidth: 2, borderColor: pricesResult.best_buy.is_expired ? WARNING : SECONDARY, background: pricesResult.best_buy.is_expired ? 'rgba(243, 156, 18, 0.04)' : 'rgba(192, 57, 43, 0.04)' }}
                  styles={{ header: { borderBottom: 'none' } }}
                >
                  {pricesResult.best_buy.is_expired && (
                    <Alert
                      type="warning"
                      showIcon
                      message="推荐时机已过期"
                      description="当前日期已超过最优购票日期，以下推荐仅供参考。"
                      style={{ marginBottom: 8 }}
                    />
                  )}
                  <Typography.Paragraph strong style={{ marginBottom: 4, color: pricesResult.best_buy.is_expired ? WARNING : SECONDARY, fontSize: 15 }}>
                    {pricesResult.best_buy.message}
                  </Typography.Paragraph>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    基于 XGBoost 模型对 {pricesResult.prices.length} 个提前天数节点的预测 · 当前日期 {pricesResult.today}
                  </Typography.Text>
                </Card>
              )}
            </div>
          ) : (
            <Card style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 160 }}>
              <Typography.Text type="secondary">
                选择航班并填写出发日期后点击「预测价格」，将预测不同提前天数下的购票价格，并通过 XGBoost + SHAP 逆向解读航司定价逻辑。
              </Typography.Text>
            </Card>
          )}
        </Col>
      </Row>

      {submitted && display && (
        <div style={{ marginTop: 24 }}>
          {pricesResult && (
            <>
              <Card title="提前天数 vs 预测价格" size="small" style={{ marginBottom: 16 }}>
                <Typography.Paragraph type="secondary" style={{ fontSize: 12, marginTop: 0, marginBottom: 8 }}>
                  不同提前购票天数对应的预测价格曲线，红色标记为最优购买时机
                </Typography.Paragraph>
                <EchartsBox option={priceCurveOption} height={320} />
              </Card>

              <Card title="各提前天数价格明细" size="small" style={{ marginBottom: 16 }}>
                <Table
                  dataSource={pricesResult.prices}
                  columns={priceTableColumns}
                  rowKey="days_prior"
                  pagination={false}
                  size="small"
                  rowClassName={(record) =>
                    record.days_prior === pricesResult.best_buy.days_prior ? 'best-row' : ''
                  }
                />
              </Card>
            </>
          )}

          {shapDetail && (
            <>
              <Card title={`SHAP 特征归因瀑布图（提前 ${display.days_prior} 天）`} size="small" style={{ marginBottom: 16 }}>
                <Typography.Paragraph type="secondary" style={{ fontSize: 12, marginTop: 0, marginBottom: 8 }}>
                  红色柱体表示推高定价的因素，蓝色柱体表示压低定价的因素。柱体越长，影响越大。
                </Typography.Paragraph>
                <EchartsBox option={waterfallOption} height={Math.max(300, (shapDetail.waterfall.length ?? 10) * 22 + 60)} />
              </Card>

              <Card title="因素类别贡献对比" size="small" style={{ marginBottom: 16 }}>
                <Typography.Paragraph type="secondary" style={{ fontSize: 12, marginTop: 0, marginBottom: 8 }}>
                  按时间、节假日、展会、航班属性、高铁竞争五大类别汇总。{' '}
                  <Tooltip title="同一类别内所有特征SHAP值的绝对值之和，无论推高还是压低都计入。反映该类别对定价的整体影响力度。">
                    <span style={{ color: TEXT_PRIMARY, cursor: 'help', borderBottom: '1px dashed #95A5A6' }}>绝对贡献</span>
                  </Tooltip>
                  {' '}反映影响强度，{' '}
                  <Tooltip title="同一类别内所有特征SHAP值的代数和（正负抵消后的净值）。正值=整体推高价格，负值=整体压低价格。">
                    <span style={{ color: TEXT_PRIMARY, cursor: 'help', borderBottom: '1px dashed #95A5A6' }}>净贡献</span>
                  </Tooltip>
                  {' '}反映方向。
                </Typography.Paragraph>
                <EchartsBox option={categoryOption} height={320} />
              </Card>

              <Card title="关键驱动因素详情" size="small" style={{ marginBottom: 16 }}>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
                  {Array.from(new Set(drivers.map((d) => d.category).filter(Boolean))).map((cat) => (
                    <span key={cat} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, color: TEXT_PRIMARY }}>
                      <span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: 2, background: CATEGORY_TAG_COLORS[cat ?? '其他'] }} />
                      {cat}
                    </span>
                  ))}
                </div>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                    <thead>
                      <tr style={{ borderBottom: `2px solid ${TEXT_MUTED}` }}>
                        <th style={{ textAlign: 'left', padding: '6px 8px', color: TEXT_MUTED }}>特征</th>
                        <th style={{ textAlign: 'left', padding: '6px 8px', color: TEXT_MUTED }}>类别</th>
                        <th style={{ textAlign: 'right', padding: '6px 8px', color: TEXT_MUTED }}>SHAP值</th>
                        <th style={{ textAlign: 'left', padding: '6px 8px', color: TEXT_MUTED }}>方向</th>
                        <th style={{ textAlign: 'right', padding: '6px 8px', color: TEXT_MUTED }}>特征值</th>
                      </tr>
                    </thead>
                    <tbody>
                      {drivers.map((d) => (
                        <tr key={d.feature} style={{ borderBottom: `1px solid ${BG_SECONDARY}` }}>
                          <td style={{ padding: '6px 8px', fontWeight: 500 }}>{featLabel(d.feature)}</td>
                          <td style={{ padding: '6px 8px' }}>
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12 }}>
                              <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: 2, background: CATEGORY_TAG_COLORS[d.category ?? '其他'] }} />
                              {d.category ?? '其他'}
                            </span>
                          </td>
                          <td style={{
                            padding: '6px 8px',
                            textAlign: 'right',
                            fontWeight: 600,
                            color: d.shap_value >= 0 ? SHAP_HIGH : SHAP_LOW,
                          }}>
                            {d.shap_value >= 0 ? '+' : ''}{d.shap_value.toFixed(1)}
                          </td>
                          <td style={{ padding: '6px 8px' }}>
                            <span style={{
                              display: 'inline-block',
                              width: 8,
                              height: 8,
                              borderRadius: '50%',
                              background: d.shap_value >= 0 ? SHAP_HIGH : SHAP_LOW,
                              marginRight: 6,
                            }} />
                            {d.shap_value >= 0 ? '推高' : '压低'}
                          </td>
                          <td style={{ padding: '6px 8px', textAlign: 'right', color: TEXT_MUTED }}>
                            {d.feature_value?.toFixed(2) ?? '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>

              <Card title="定价归因解读" size="small" style={{ marginBottom: 16 }}>
                <Typography.Paragraph style={{ lineHeight: 1.8, margin: 0 }}>
                  {interpretation}
                </Typography.Paragraph>
              </Card>
            </>
          )}
        </div>
      )}
    </div>
  );
}
