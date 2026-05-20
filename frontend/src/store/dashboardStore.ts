import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { OverviewResponse } from '../types/overview';

export interface DashboardState {
  currentPage: string;
  loading: boolean;
  error: string | null;
  /** 当前页主要业务数据（阶段二以概览为主，类型为 Overview） */
  data: OverviewResponse | null;
}

export interface DashboardActions {
  setPage: (page: string) => void;
  setLoading: (loading: boolean) => void;
  setData: (data: OverviewResponse | null) => void;
  setError: (error: string | null) => void;
}

/** 全局请求计数，避免并发请求时 loading 提前关闭 */
let activeRequestCount = 0;

export function beginApiRequest(): void {
  activeRequestCount += 1;
  useDashboardStore.getState().setLoading(true);
}

export function endApiRequest(): void {
  activeRequestCount = Math.max(0, activeRequestCount - 1);
  if (activeRequestCount === 0) {
    useDashboardStore.getState().setLoading(false);
  }
}

export const useDashboardStore = create<DashboardState & DashboardActions>()(
  devtools(
    (set) => ({
      currentPage: '/',
      loading: false,
      error: null,
      data: null,
      setPage: (page) => set({ currentPage: page }),
      setLoading: (loading) => set({ loading }),
      setData: (data) => set({ data }),
      setError: (error) => set({ error }),
    }),
    { name: 'DashboardStore' },
  ),
);
