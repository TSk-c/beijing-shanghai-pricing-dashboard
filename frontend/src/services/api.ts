import axios, { type AxiosError } from 'axios';
import type {
  DataPanoramaResponse,
  EdaChartsResponse,
  ModelComparisonResponse,
  ModelPerformanceResponse,
  PredictResponse,
  PriceDistributionResponse,
  RpaTrendResponse,
} from '../types/api';
import type { OverviewResponse } from '../types/overview';
import { beginApiRequest, endApiRequest, useDashboardStore } from '../store/dashboardStore';
import { getMessageInstance } from './messageHolder';
import {
  mockModelComparison,
  mockOverview,
  mockPredictResult,
  mockPriceDistribution,
  mockRpaTrend,
} from './mockData';

const baseURL = import.meta.env.VITE_API_BASE_URL ?? '';

function _warn(text: string) {
  try { getMessageInstance().warning(text); } catch { /* not initialized */ }
}
function _error(text: string) {
  try { getMessageInstance().error(text); } catch { /* not initialized */ }
}

const _cache = new Map<string, Promise<unknown>>();

async function cachedFetch<T>(key: string, fetcher: () => Promise<T>): Promise<T> {
  if (_cache.has(key)) {
    return _cache.get(key) as Promise<T>;
  }
  const promise = fetcher().catch((err) => {
    _cache.delete(key);
    throw err;
  });
  _cache.set(key, promise);
  return promise;
}

export const apiClient = axios.create({
  baseURL,
  timeout: 60_000,
});

apiClient.interceptors.request.use(
  (config) => {
    beginApiRequest();
    return config;
  },
  (error) => {
    endApiRequest();
    return Promise.reject(error);
  },
);

apiClient.interceptors.response.use(
  (response) => {
    endApiRequest();
    return response;
  },
  (error: AxiosError<{ detail?: string | { msg?: string }[] }>) => {
    endApiRequest();
    const cfg = error.config;
    const skip = Boolean(cfg?.skipErrorToast);
    if (!skip) {
      const raw = error.response?.data?.detail;
      let msg: string;
      if (typeof raw === 'string') {
        msg = raw;
      } else if (Array.isArray(raw)) {
        msg = raw.map((x) => (typeof x === 'object' && x && 'msg' in x ? String((x as { msg: string }).msg) : '')).join('; ') || '请求参数校验失败';
      } else {
        msg = error.message || '请求失败，请稍后重试';
      }
      useDashboardStore.getState().setError(msg);
      _error(msg);
    }
    return Promise.reject(error);
  },
);

export async function fetchOverview(): Promise<OverviewResponse> {
  return cachedFetch('overview', async () => {
    try {
      const { data } = await apiClient.get<OverviewResponse>('/api/overview', {
        skipErrorToast: true,
      });
      return data;
    } catch {
      _warn('概览接口暂不可用，已展示本地 Mock 数据');
      return {
        total_records: mockOverview.total_records,
        hsr_coverage: mockOverview.hsr_coverage,
        date_range: { ...mockOverview.date_range },
        best_model_mape: mockOverview.best_model_mape,
      };
    }
  });
}

export async function fetchPriceDistribution(): Promise<PriceDistributionResponse> {
  return cachedFetch('priceDistribution', async () => {
    try {
      const { data } = await apiClient.get<PriceDistributionResponse>('/api/price/distribution', {
        skipErrorToast: true,
      });
      return data;
    } catch {
      _warn('票价分布接口暂不可用，已展示本地 Mock 数据');
      return {
        bins: mockPriceDistribution.bins.map((b) => ({ ...b })),
        median: mockPriceDistribution.median,
        mean: mockPriceDistribution.mean,
        skewness: mockPriceDistribution.skewness,
        kurtosis: mockPriceDistribution.kurtosis,
      };
    }
  });
}

export async function fetchRpaTrend(): Promise<RpaTrendResponse> {
  return cachedFetch('rpaTrend', async () => {
    try {
      const { data } = await apiClient.get<RpaTrendResponse>('/api/rail-air/rpa-trend', {
        skipErrorToast: true,
      });
      return data;
    } catch {
      _warn('RPA 时序接口暂不可用，已展示本地 Mock 数据');
      return {
        dates: [...mockRpaTrend.dates],
        airPrices: [...mockRpaTrend.airPrices],
        rpaValues: [...mockRpaTrend.rpaValues],
        hsrSecond: [...mockRpaTrend.hsrSecond],
        hsrFirst: [...mockRpaTrend.hsrFirst],
        hsrBusiness: [...mockRpaTrend.hsrBusiness],
        weekends: [...mockRpaTrend.weekends],
        holidays: { ...mockRpaTrend.holidays },
        pearson_r: mockRpaTrend.pearson_r,
        pearson_p: mockRpaTrend.pearson_p,
      };
    }
  });
}

export async function fetchModelComparison(): Promise<ModelComparisonResponse> {
  return cachedFetch('modelComparison', async () => {
    try {
      const { data } = await apiClient.get<ModelComparisonResponse>('/api/model/comparison', {
        skipErrorToast: true,
      });
      return data;
    } catch {
      _warn('模型对比接口暂不可用，已展示本地 Mock 数据');
      return {
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
    }
  });
}

export async function fetchDataPanorama(): Promise<DataPanoramaResponse> {
  return cachedFetch('dataPanorama', async () => {
    const { data } = await apiClient.get<DataPanoramaResponse>('/api/data-panorama');
    return data;
  });
}

export interface PredictionCoverageResponse {
  dep_date_range: { min: string; max: string };
  query_date_range: { min: string; max: string };
  days_prior_range: { min: number; max: number };
  flight_count: number;
  total_rows: number;
  method: string;
  note: string;
}

export async function fetchPredictionCoverage(): Promise<PredictionCoverageResponse> {
  const { data } = await apiClient.get<PredictionCoverageResponse>('/api/model/prediction-coverage');
  return data;
}

export async function fetchEdaCharts(): Promise<EdaChartsResponse> {
  return cachedFetch('edaCharts', async () => {
    try {
      const { data } = await apiClient.get<EdaChartsResponse>('/api/eda/charts', {
        skipErrorToast: true,
      });
      return data;
    } catch {
      _warn('EDA 可视化接口暂不可用，请检查后端服务');
      throw new Error('EDA API unavailable');
    }
  });
}

export interface ModelOverviewData {
  overall: ModelPerformanceResponse['overall'];
  window_metrics: ModelPerformanceResponse['window_metrics'];
  scenario_metrics: ModelPerformanceResponse['scenario_metrics'];
  n_features: number;
}

export interface ModelShapData {
  shap_global: ModelPerformanceResponse['shap_global'];
}

export interface ModelHsrData {
  hsr_contribution: ModelPerformanceResponse['hsr_contribution'];
}

export interface ModelSensitivityData {
  sensitivity: ModelPerformanceResponse['sensitivity'];
}

export async function fetchModelOverview(): Promise<ModelOverviewData> {
  return cachedFetch('modelOverview', async () => {
    try {
      const { data } = await apiClient.get<ModelOverviewData>('/api/model/performance/overview', {
        skipErrorToast: true,
        timeout: 60_000,
      });
      return data;
    } catch {
      _warn('模型概览接口暂不可用');
      throw new Error('Model Overview API unavailable');
    }
  });
}

export async function fetchModelShap(): Promise<ModelShapData> {
  return cachedFetch('modelShap', async () => {
    try {
      const { data } = await apiClient.get<ModelShapData>('/api/model/performance/shap', {
        skipErrorToast: true,
        timeout: 120_000,
      });
      return data;
    } catch {
      _warn('SHAP解释接口暂不可用');
      throw new Error('Model SHAP API unavailable');
    }
  });
}

export async function fetchModelHsr(): Promise<ModelHsrData> {
  return cachedFetch('modelHsr', async () => {
    try {
      const { data } = await apiClient.get<ModelHsrData>('/api/model/performance/hsr', {
        skipErrorToast: true,
        timeout: 120_000,
      });
      return data;
    } catch {
      _warn('高铁贡献度接口暂不可用');
      throw new Error('Model HSR API unavailable');
    }
  });
}

export async function fetchModelSensitivity(): Promise<ModelSensitivityData> {
  return cachedFetch('modelSensitivity', async () => {
    try {
      const { data } = await apiClient.get<ModelSensitivityData>('/api/model/performance/sensitivity', {
        skipErrorToast: true,
        timeout: 180_000,
      });
      return data;
    } catch {
      _warn('超参敏感性接口暂不可用');
      throw new Error('Model Sensitivity API unavailable');
    }
  });
}

export const MOCK_FEATURE_VECTOR_41: number[] = Array.from({ length: 41 }, (_, i) =>
  i === 0 ? 7.0 : Math.sin(i / 5) * 0.1,
);

export async function postModelPredict(features: number[]): Promise<PredictResponse> {
  try {
    const { data } = await apiClient.post<PredictResponse>(
      '/api/model/predict',
      { features },
      { skipErrorToast: true },
    );
    return data;
  } catch {
    _warn('预测接口暂不可用，已展示本地 Mock 数据');
    return {
      predicted_price: mockPredictResult.predicted_price,
      confidence_interval: [
        mockPredictResult.confidence_interval[0],
        mockPredictResult.confidence_interval[1],
      ],
      prediction_interval_95: [
        mockPredictResult.prediction_interval_95[0],
        mockPredictResult.prediction_interval_95[1],
      ],
      key_drivers: mockPredictResult.key_drivers.map((d) => ({ ...d })),
      competitive_status: { ...mockPredictResult.competitive_status },
    };
  }
}

export async function postModelPredictFlight(
  flightNo: string,
  depDate: string,
  daysPrior: number,
): Promise<PredictResponse> {
  const { data } = await apiClient.post<PredictResponse>(
    '/api/model/predict-flight',
    { flight_no: flightNo, dep_date: depDate, days_prior: daysPrior },
    { skipErrorToast: true, timeout: 120_000 },
  );
  return data;
}

export interface PriceByDaysPrior {
  days_prior: number;
  predicted_price: number;
  purchase_date: string;
  is_expired: boolean;
  expired_note: string;
}

export interface PredictFlightPricesResponse {
  flight_no: string;
  dep_date: string;
  today: string;
  remaining_days: number;
  reference_price: number | null;
  prices: PriceByDaysPrior[];
  best_buy: {
    days_prior: number;
    predicted_price: number;
    purchase_date: string;
    is_expired: boolean;
    message: string;
  };
}

export async function postModelPredictFlightPrices(
  flightNo: string,
  depDate: string,
): Promise<PredictFlightPricesResponse> {
  const { data } = await apiClient.post<PredictFlightPricesResponse>(
    '/api/model/predict-flight-prices',
    { flight_no: flightNo, dep_date: depDate },
    { skipErrorToast: true, timeout: 120_000 },
  );
  return data;
}

export interface FlightsByDateResponse {
  dep_date: string;
  flights: string[];
}

export async function fetchFlightsByDate(depDate: string): Promise<FlightsByDateResponse> {
  const { data } = await apiClient.get<FlightsByDateResponse>('/api/model/flights-by-date', {
    params: { dep_date: depDate },
    skipErrorToast: true,
  });
  return data;
}

export interface FlightInfo {
  flight_no: string;
  airline: string;
  dep_airport: string;
  arr_airport: string;
  dep_time: string;
  arr_time: string;
  duration: number;
}

export async function fetchFlights(): Promise<FlightInfo[]> {
  return cachedFetch('flights', async () => {
    const { data } = await apiClient.get<FlightInfo[]>('/api/model/flights');
    return data;
  });
}
