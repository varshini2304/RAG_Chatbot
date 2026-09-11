import { create } from 'zustand';
import { analyticsService } from '../services/api/analyticsService';

export interface ChartDataPoint {
  date: string;
  conversations: number;
  responseTime: number;
  errors: number;
  requests: number;
}

export interface ProviderShare {
  name: string;
  value: number;
  percentage?: string;
  share_pct?: number;
  color?: string;
}

interface AnalyticsState {
  trendData: ChartDataPoint[];
  providerShares: ProviderShare[];
  isLoading: boolean;
  error: string | null;
  fetchAnalyticsData: () => Promise<void>;
}

export const useAnalyticsStore = create<AnalyticsState>((set) => ({
  trendData: [],
  providerShares: [],
  isLoading: false,
  error: null,

  fetchAnalyticsData: async () => {
    set({ isLoading: true, error: null });
    try {
      const data = await analyticsService.getAnalyticsData();
      set({
        trendData: data?.trendData || [],
        providerShares: data?.providerShares || [],
        isLoading: false,
        error: null,
      });
    } catch (err: unknown) {
      const msg = err && typeof err === 'object' && 'message' in err ? String((err as { message?: string }).message) : 'Failed to fetch analytics data from backend.';
      set({
        isLoading: false,
        error: msg,
      });
    }
  },
}));
