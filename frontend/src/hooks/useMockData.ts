import { useCallback, useMemo, useState } from 'react';
import {
  mockAirlineCompare,
  mockBookingCurve,
  mockElasticity,
  mockHeatmap,
  mockModelComparison,
  mockOverview,
  mockPredictResult,
  mockPriceDistribution,
  mockRpaTrend,
  mockShapGlobal,
  mockWindowPerformance,
} from '../services/mockData';

/** Mock 请求模拟延迟（毫秒） */
export const MOCK_DELAY_MS = 1000;

async function delay<T>(value: T): Promise<T> {
  await new Promise<void>((resolve) => {
    setTimeout(resolve, MOCK_DELAY_MS);
  });
  return value;
}

/**
 * 各数据集延迟获取（与真实 API 形态一致，便于后续替换为 axios）
 * 每次调用会等待 MOCK_DELAY_MS，并返回当前 mock 快照。
 */
export const mockDataFetchers = {
  fetchOverview: () => delay(mockOverview),
  fetchPriceDistribution: () => delay(mockPriceDistribution),
  fetchBookingCurve: () => delay(mockBookingCurve),
  fetchRpaTrend: () => delay(mockRpaTrend),
  fetchElasticity: () => delay(mockElasticity),
  fetchModelComparison: () => delay(mockModelComparison),
  fetchShapGlobal: () => delay(mockShapGlobal),
  fetchWindowPerformance: () => delay(mockWindowPerformance),
  fetchPredictResult: () => delay(mockPredictResult),
  fetchHeatmap: () => delay(mockHeatmap),
  fetchAirlineCompare: () => delay(mockAirlineCompare),
};

/**
 * 统一 Mock 数据加载：维护最近一次请求的 data / loading / error，
 * 并提供与各数据集对应的 load 方法（每次调用均含 1s 模拟延迟）。
 */
export function useMockData() {
  const [data, setData] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async <T,>(fn: () => Promise<T>): Promise<T | undefined> => {
    setLoading(true);
    setError(null);
    try {
      const result = await fn();
      setData(result);
      return result;
    } catch (e) {
      const msg = e instanceof Error ? e.message : '加载失败';
      setError(msg);
      return undefined;
    } finally {
      setLoading(false);
    }
  }, []);

  return useMemo(
    () => ({
      data,
      loading,
      error,
      loadOverview: () => run(mockDataFetchers.fetchOverview),
      loadPriceDistribution: () => run(mockDataFetchers.fetchPriceDistribution),
      loadBookingCurve: () => run(mockDataFetchers.fetchBookingCurve),
      loadRpaTrend: () => run(mockDataFetchers.fetchRpaTrend),
      loadElasticity: () => run(mockDataFetchers.fetchElasticity),
      loadModelComparison: () => run(mockDataFetchers.fetchModelComparison),
      loadShapGlobal: () => run(mockDataFetchers.fetchShapGlobal),
      loadWindowPerformance: () => run(mockDataFetchers.fetchWindowPerformance),
      loadPredictResult: () => run(mockDataFetchers.fetchPredictResult),
      loadHeatmap: () => run(mockDataFetchers.fetchHeatmap),
      loadAirlineCompare: () => run(mockDataFetchers.fetchAirlineCompare),
    }),
    [data, error, loading, run],
  );
}
