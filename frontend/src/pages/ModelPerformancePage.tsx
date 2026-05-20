import { useEffect, useMemo, useState } from 'react';
import { Alert, Button, Card, Col, Descriptions, Row, Skeleton, Table, Tabs, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { EchartsBox } from '../components/EchartsBox';
import {
  fetchModelHsr,
  fetchModelOverview,
  fetchModelSensitivity,
  fetchModelShap,
} from '../services/api';
import type { ModelOverviewData } from '../services/api';
import {
  buildHsrContributionPieOption,
  buildHsrContributionWaterfallOption,
  buildPeriodContributionOption,
  buildSensitivityLineOption,
  buildShapSwarmOption,
  buildWindowRadarOption,
} from '../chartConfigs/modelCharts';

const PARAM_LABELS: Record<string, string> = {
  learning_rate: '学习率',
  max_depth: '最大深度',
  subsample: '子采样率',
  colsample_bytree: '列采样率',
  reg_alpha: 'L1正则',
  reg_lambda: 'L2正则',
  min_child_weight: '最小子节点权重',
};

function useAsyncLoader<T>(fetcher: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const d = await fetcher();
        if (!cancelled) setData(d);
      } catch {
        if (!cancelled) setError(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const refetch = () => {
    setLoading(true);
    setError(false);
    let cancelled = false;
    (async () => {
      try {
        const d = await fetcher();
        if (!cancelled) setData(d);
      } catch {
        if (!cancelled) setError(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  };

  return { data, loading, error, refetch };
}

function SectionCard({ title, loading, error, children, onRetry }: {
  title: string;
  loading: boolean;
  error: boolean;
  children: React.ReactNode;
  onRetry?: () => void;
}) {
  return (
    <Card title={title} style={{ marginBottom: 16 }} styles={{ body: { paddingTop: 8 } }}>
      {loading ? (
        <Skeleton active paragraph={{ rows: 4 }} />
      ) : error ? (
        <Alert
          type="error"
          message="数据加载失败"
          action={onRetry ? <Button size="small" onClick={onRetry}>重试</Button> : undefined}
        />
      ) : (
        children
      )}
    </Card>
  );
}

export function ModelPerformancePage() {
  const overview = useAsyncLoader(fetchModelOverview);
  const shap = useAsyncLoader(fetchModelShap);
  const hsr = useAsyncLoader(fetchModelHsr);
  const sensitivity = useAsyncLoader(fetchModelSensitivity);

  const sortedWindowMetrics = useMemo(() => {
    if (!overview.data) return [];
    const items = [...overview.data.window_metrics];
    items.sort((a, b) => {
      const numA = parseInt(a.window, 10);
      const numB = parseInt(b.window, 10);
      const isLastA = a.window.includes('+') || a.window.includes('天+');
      const isLastB = b.window.includes('+') || b.window.includes('天+');
      if (isLastA && !isLastB) return 1;
      if (!isLastA && isLastB) return -1;
      return numA - numB;
    });
    return items;
  }, [overview.data]);

  const radarOption = useMemo(() => {
    if (!overview.data) return {};
    return buildWindowRadarOption(sortedWindowMetrics);
  }, [overview.data, sortedWindowMetrics]);

  const shapOption = useMemo(() => {
    if (!shap.data || !shap.data.shap_global.length) return {};
    return buildShapSwarmOption(shap.data.shap_global);
  }, [shap.data]);

  const hsrPieOption = useMemo(() => {
    if (!hsr.data) return {};
    return buildHsrContributionPieOption(hsr.data.hsr_contribution.feature_contributions);
  }, [hsr.data]);

  const hsrWaterfallOption = useMemo(() => {
    if (!hsr.data) return {};
    return buildHsrContributionWaterfallOption(hsr.data.hsr_contribution.feature_contributions);
  }, [hsr.data]);

  const periodOption = useMemo(() => {
    if (!hsr.data || !hsr.data.hsr_contribution.period_contributions.length) return {};
    const items = [...hsr.data.hsr_contribution.period_contributions];
    items.sort((a, b) => {
      const numA = parseInt(a.period, 10);
      const numB = parseInt(b.period, 10);
      const isLastA = a.period.includes('+') || a.period.includes('天+');
      const isLastB = b.period.includes('+') || b.period.includes('天+');
      if (isLastA && !isLastB) return 1;
      if (!isLastA && isLastB) return -1;
      return numA - numB;
    });
    return buildPeriodContributionOption(items);
  }, [hsr.data]);

  const sensitivityOptions = useMemo(() => {
    if (!sensitivity.data) return {} as Record<string, ReturnType<typeof buildSensitivityLineOption>>;
    const opts: Record<string, ReturnType<typeof buildSensitivityLineOption>> = {};
    for (const [param, values] of Object.entries(sensitivity.data.sensitivity)) {
      opts[param] = buildSensitivityLineOption(PARAM_LABELS[param] ?? param, values);
    }
    return opts;
  }, [sensitivity.data]);

  const windowColumns: ColumnsType<ModelOverviewData['window_metrics'][0]> = [
    { title: '窗口', dataIndex: 'window', key: 'window', fixed: 'left', width: 100 },
    { title: '样本量', dataIndex: 'n', key: 'n', width: 80 },
    { title: 'MAPE(%)', dataIndex: 'mape', key: 'mape', sorter: (a, b) => a.mape - b.mape, width: 100 },
    { title: 'RMSE', dataIndex: 'rmse', key: 'rmse', sorter: (a, b) => a.rmse - b.rmse, width: 90 },
    { title: 'MAE', dataIndex: 'mae', key: 'mae', sorter: (a, b) => a.mae - b.mae, width: 90 },
  ];

  const scenarioColumns: ColumnsType<ModelOverviewData['scenario_metrics'][0]> = [
    { title: '情景', dataIndex: 'scenario', key: 'scenario', fixed: 'left', width: 110 },
    { title: '样本量', dataIndex: 'n', key: 'n', width: 80 },
    { title: 'MAPE(%)', dataIndex: 'mape', key: 'mape', sorter: (a, b) => a.mape - b.mape, width: 100 },
    { title: 'RMSE', dataIndex: 'rmse', key: 'rmse', sorter: (a, b) => a.rmse - b.rmse, width: 90 },
    { title: 'MAE', dataIndex: 'mae', key: 'mae', sorter: (a, b) => a.mae - b.mae, width: 90 },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={4} style={{ marginTop: 0 }}>
        XGBoost 定价模型性能
      </Typography.Title>
      <Typography.Paragraph type="secondary">
        基于 {overview.data?.n_features ?? '…'} 维特征训练的 XGBoost 回归模型，70/30 时间序列划分，early stopping。
      </Typography.Paragraph>

      <SectionCard title="整体性能" loading={overview.loading} error={overview.error} onRetry={overview.refetch}>
        {overview.data && (
          <Descriptions bordered size="small" column={4}>
            <Descriptions.Item label="样本量">{overview.data.overall.n}</Descriptions.Item>
            <Descriptions.Item label="MAPE(%)">{overview.data.overall.mape}</Descriptions.Item>
            <Descriptions.Item label="RMSE">{overview.data.overall.rmse}</Descriptions.Item>
            <Descriptions.Item label="MAE">{overview.data.overall.mae}</Descriptions.Item>
          </Descriptions>
        )}
      </SectionCard>

      <SectionCard title="分提前期窗口性能" loading={overview.loading} error={overview.error} onRetry={overview.refetch}>
        {overview.data && (
          <Row gutter={[16, 16]}>
            <Col xs={24} lg={14}>
              <Table
                columns={windowColumns}
                dataSource={sortedWindowMetrics}
                rowKey="window"
                size="small"
                scroll={{ x: 1000 }}
                pagination={false}
              />
            </Col>
            <Col xs={24} lg={10}>
              <EchartsBox option={radarOption} height={360} />
            </Col>
          </Row>
        )}
      </SectionCard>

      <SectionCard title="分出行情景性能" loading={overview.loading} error={overview.error} onRetry={overview.refetch}>
        {overview.data && (
          <Table
            columns={scenarioColumns}
            dataSource={overview.data.scenario_metrics}
            rowKey="scenario"
            size="small"
            scroll={{ x: 1000 }}
            pagination={false}
          />
        )}
      </SectionCard>

      <SectionCard title="SHAP 全局解释（蜂群图）" loading={shap.loading} error={shap.error} onRetry={shap.refetch}>
        <Typography.Paragraph type="secondary" style={{ marginBottom: 8, fontSize: 12 }}>
          每个点代表一个样本，横轴为 SHAP 值（正值推高预测，负值压低），颜色由蓝（低）到红（高）表示特征取值大小。
        </Typography.Paragraph>
        {shap.data && <EchartsBox option={shapOption} height={500} />}
      </SectionCard>

      <SectionCard title="高铁竞争特征贡献度" loading={hsr.loading} error={hsr.error} onRetry={hsr.refetch}>
        {hsr.data && (
          <>
            <Row gutter={[16, 16]}>
              <Col xs={24} md={8}>
                <Typography.Paragraph type="secondary" style={{ fontSize: 12 }}>
                  全部样本中高铁特征平均贡献占比：{hsr.data.hsr_contribution.overall_pct}%；
                  高铁有效样本中：{hsr.data.hsr_contribution.available_pct}%。
                </Typography.Paragraph>
                <EchartsBox option={hsrPieOption} height={280} />
              </Col>
              <Col xs={24} md={16}>
                <EchartsBox option={hsrWaterfallOption} height={400} />
              </Col>
            </Row>
            {hsr.data.hsr_contribution.period_contributions.length > 0 && (
              <>
                <Typography.Title level={5} style={{ marginTop: 16 }}>分提前期贡献占比</Typography.Title>
                <EchartsBox option={periodOption} height={260} />
              </>
            )}
          </>
        )}
      </SectionCard>

      <SectionCard title="超参数敏感性" loading={sensitivity.loading} error={sensitivity.error} onRetry={sensitivity.refetch}>
        <Typography.Paragraph type="secondary" style={{ marginBottom: 8, fontSize: 12 }}>
          逐个调整超参数（其余固定），观察 RMSE / MAE / MAPE 的变化趋势。
        </Typography.Paragraph>
        {sensitivity.data && (
          <Tabs
            items={Object.entries(sensitivityOptions).map(([param, option]) => ({
              key: param,
              label: PARAM_LABELS[param] ?? param,
              children: <EchartsBox option={option} height={360} />,
            }))}
          />
        )}
      </SectionCard>
    </div>
  );
}
