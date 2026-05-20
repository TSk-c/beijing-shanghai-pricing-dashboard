import { useEffect, useMemo, useState } from 'react';
import { Alert, Card, Col, Row, Table, Tabs, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { EchartsBox } from '../components/EchartsBox';
import { fetchModelComparison } from '../services/api';
import { mockModelComparison } from '../services/mockData';
import type { ModelComparisonResponse } from '../types/api';
import type { ModelComparisonRow } from '../types/modelComparison';
import {
  buildModelComparisonGroupedBar,
  buildModelComparisonOverallBar,
} from '../chartConfigs/modelComparisonCharts';
import { SUCCESS, TEXT_MUTED } from '../constants/colors';

const METRICS = ['MAE', 'MAPE', 'RMSE'] as const;
type MetricKey = 'mae' | 'mape' | 'rmse';
const METRIC_KEY_MAP: Record<string, MetricKey> = {
  MAE: 'mae',
  MAPE: 'mape',
  RMSE: 'rmse',
};

const initialPayload: ModelComparisonResponse = {
  models: [...mockModelComparison.models],
  layers: [...mockModelComparison.layers],
  overall: {
    mae: [...mockModelComparison.overall.mae],
    mape: [...mockModelComparison.overall.mape],
    rmse: [...mockModelComparison.overall.rmse],
  },
  layered: Object.fromEntries(
    Object.entries(mockModelComparison.layered).map(([k, v]) => [
      k,
      { mae: [...v.mae], mape: [...v.mape], rmse: [...v.rmse] },
    ]),
  ),
};

function buildTableRows(payload: ModelComparisonResponse): ModelComparisonRow[] {
  const rows: ModelComparisonRow[] = [];
  const allLayers = ['整体', ...payload.layers];
  const dataMap: Record<string, { mae: (number | null)[]; mape: (number | null)[]; rmse: (number | null)[] }> = {
    整体: payload.overall,
    ...payload.layered,
  };

  for (const layer of allLayers) {
    const layerData = dataMap[layer];
    if (!layerData) continue;
    for (let mi = 0; mi < METRICS.length; mi++) {
      const metric = METRICS[mi];
      const key = METRIC_KEY_MAP[metric];
      rows.push({
        key: `${layer}-${metric}`,
        layer,
        layerRowSpan: mi === 0 ? 3 : 0,
        metric,
        values: layerData[key],
      });
    }
  }
  return rows;
}

function findBestIndex(values: (number | null)[]): number {
  let bestIdx = -1;
  let bestVal = Infinity;
  for (let i = 0; i < values.length; i++) {
    const v = values[i];
    if (v != null && v < bestVal) {
      bestVal = v;
      bestIdx = i;
    }
  }
  return bestIdx;
}

export function ModelComparisonPage() {
  const [loading, setLoading] = useState(true);
  const [payload, setPayload] = useState<ModelComparisonResponse>(initialPayload);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchModelComparison();
        if (!cancelled) setPayload(data);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const { models: rawModels, layers, overall: rawOverall, layered: rawLayered } = payload;

  const { models, overall, layered, reorderedPayload } = useMemo(() => {
    const xgbIdx = rawModels.indexOf('XGBoost');
    if (xgbIdx <= 0) {
      return {
        models: rawModels,
        overall: rawOverall,
        layered: rawLayered,
        reorderedPayload: { models: rawModels, layers, overall: rawOverall, layered: rawLayered } as ModelComparisonResponse,
      };
    }

    const reordered = [...rawModels];
    reordered.splice(xgbIdx, 1);
    reordered.unshift('XGBoost');

    const reorderValues = (arr: (number | null)[]) => {
      if (arr.length !== rawModels.length) return arr;
      const copy = [...arr];
      const [xgbVal] = copy.splice(xgbIdx, 1);
      copy.unshift(xgbVal);
      return copy;
    };

    const reorderedOverall = {
      mae: reorderValues(rawOverall.mae),
      mape: reorderValues(rawOverall.mape),
      rmse: reorderValues(rawOverall.rmse),
    };

    const reorderedLayered: typeof rawLayered = {};
    for (const [layer, metrics] of Object.entries(rawLayered)) {
      reorderedLayered[layer] = {
        mae: reorderValues(metrics.mae),
        mape: reorderValues(metrics.mape),
        rmse: reorderValues(metrics.rmse),
      };
    }

    return {
      models: reordered,
      overall: reorderedOverall,
      layered: reorderedLayered,
      reorderedPayload: {
        models: reordered,
        layers,
        overall: reorderedOverall,
        layered: reorderedLayered,
      } as ModelComparisonResponse,
    };
  }, [rawModels, rawOverall, rawLayered, layers]);

  const rows = useMemo(() => buildTableRows(reorderedPayload), [reorderedPayload]);

  const allLayers = useMemo(() => ['整体', ...layers], [layers]);
  const dataMap = useMemo(
    () => ({ 整体: overall, ...layered }),
    [overall, layered],
  );

  const columns: ColumnsType<ModelComparisonRow> = useMemo(
    () => [
      {
        title: '分层',
        dataIndex: 'layer',
        key: 'layer',
        width: 130,
        fixed: 'left',
        onCell: (record: ModelComparisonRow) => ({ rowSpan: record.layerRowSpan }),
      },
      {
        title: '指标',
        dataIndex: 'metric',
        key: 'metric',
        width: 80,
        render: (val: string) => <span style={{ fontWeight: 500 }}>{val}</span>,
      },
      ...models.map((model, idx) => ({
        title: model,
        key: model,
        width: 100,
        render: (_: unknown, record: ModelComparisonRow) => {
          const v = record.values[idx];
          if (v == null) return <span style={{ color: TEXT_MUTED }}>-</span>;
          const bestIdx = findBestIndex(record.values);
          const isBest = idx === bestIdx;
          const formatted = record.metric === 'MAPE' ? `${v.toFixed(2)}%` : v.toFixed(2);
          return isBest ? (
            <span style={{ color: SUCCESS, fontWeight: 700 }}>{formatted}</span>
          ) : (
            <span>{formatted}</span>
          );
        },
      })),
    ],
    [models],
  );

  const overallChartOptions = useMemo(() => {
    const opts: Record<string, ReturnType<typeof buildModelComparisonOverallBar>> = {};
    for (const [label, key] of Object.entries(METRIC_KEY_MAP)) {
      opts[label] = buildModelComparisonOverallBar(models, overall[key], label);
    }
    return opts;
  }, [models, overall]);

  const groupedChartOptions = useMemo(() => {
    const opts: Record<string, ReturnType<typeof buildModelComparisonGroupedBar>> = {};
    for (const [label, key] of Object.entries(METRIC_KEY_MAP)) {
      opts[label] = buildModelComparisonGroupedBar(allLayers, models, dataMap, key);
    }
    return opts;
  }, [allLayers, models, dataMap]);

  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={4} style={{ marginTop: 0 }}>
        模型对比
      </Typography.Title>
      <Alert
        type="success"
        showIcon
        message="结论"
        description="XGBoost 整体最优（MAPE=6.46%），临期预测优势尤为显著；LSTM 因样本量与特征工程不足表现最差。"
        style={{ marginBottom: 16 }}
      />

      <Card
        title="分层指标对比表"
        style={{ marginBottom: 16 }}
        styles={{ body: { padding: 0 } }}
      >
        <Table<ModelComparisonRow>
          columns={columns}
          dataSource={rows}
          rowKey="key"
          loading={loading}
          size="middle"
          bordered
          pagination={false}
          scroll={{ x: 'max-content' }}
        />
      </Card>

      <Card title="整体对比" style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={8}>
            <EchartsBox option={overallChartOptions['MAE'] ?? {}} height={340} />
          </Col>
          <Col xs={24} lg={8}>
            <EchartsBox option={overallChartOptions['MAPE'] ?? {}} height={340} />
          </Col>
          <Col xs={24} lg={8}>
            <EchartsBox option={overallChartOptions['RMSE'] ?? {}} height={340} />
          </Col>
        </Row>
      </Card>

      <Card title="分层对比" styles={{ body: { paddingTop: 8 } }}>
        <Tabs
          style={{ minHeight: 420 }}
          items={METRICS.map((metric) => ({
            key: metric,
            label: metric,
            children: (
              <div style={{ paddingTop: 8 }}>
                <EchartsBox
                    option={groupedChartOptions[metric] ?? {}}
                    height={520}
                  />
              </div>
            ),
          }))}
        />
      </Card>
    </div>
  );
}
