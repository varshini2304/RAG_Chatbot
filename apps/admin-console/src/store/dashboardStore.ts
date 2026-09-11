import { create } from 'zustand';
import { dashboardService } from '../services/api/dashboardService';

export interface Metric {
  title: string;
  value: string | number;
  change: string;
  trend: 'up' | 'down';
  trendType?: 'positive' | 'negative';
  sparkline?: number[];
}

export interface SystemHealthState {
  api_status?: string;
  apiStatus?: string;
  chroma_db?: string;
  chromaDb?: string;
  vector_db_status?: string;
  embedding_service?: string;
  embeddingService?: string;
  embedding_status?: string;
  ollama_server?: string;
  ollamaServer?: string;
  ollama_server_status?: string;
  cpu_usage_pct?: number;
  memory_usage_pct?: number;
  disk_usage_pct?: number;
  cpuUsage?: number;
  memoryUsage?: number;
  diskUsage?: number;
  chunkCount?: number;
}

export interface ProviderStatusState {
  activeProvider?: string;
  active_provider?: string;
  activeModel?: string;
  active_model?: string;
  circuitBreakerStatus?: string;
  fallbackActive?: boolean;
  offlineMode?: boolean;
}

export interface ErrorEvent {
  id?: string;
  time: string;
  timestamp?: string;
  level?: string;
  module?: string;
  type: string;
  provider: string;
  message?: string;
  detail?: string;
  status: 'Resolved' | 'Retrying' | 'Failed' | 'Critical';
}

export interface ActivityEvent {
  id?: string;
  title?: string;
  description?: string;
  timestamp?: string;
  time?: string;
  type?: string;
}

let _providerPollTimer: ReturnType<typeof setInterval> | null = null;

interface DashboardState {
  metrics: Record<string, Metric>;
  systemHealth: SystemHealthState | null;
  providerStatus: ProviderStatusState | null;
  recentErrors: ErrorEvent[];
  recentActivities: ActivityEvent[];
  isLoading: boolean;
  error: string | null;
  fetchDashboardData: () => Promise<void>;
  pollProviderStatus: () => Promise<void>;
  startProviderPolling: () => void;
  stopProviderPolling: () => void;
}

export const useDashboardStore = create<DashboardState>((set, get) => ({
  metrics: {},
  systemHealth: null,
  providerStatus: null,
  recentErrors: [],
  recentActivities: [],
  isLoading: false,
  error: null,

  fetchDashboardData: async () => {
    set({ isLoading: true, error: null });
    try {
      const [overviewRes, healthRes, errorsRes] = await Promise.all([
        dashboardService.getOverviewMetrics(),
        dashboardService.getSystemHealth(),
        dashboardService.getRecentErrors(),
      ]);

      const metricsObj = overviewRes?.metrics || {};
      const provStatus = overviewRes?.providerStatus || overviewRes?.provider_status || null;
      const activitiesArr = overviewRes?.recentActivities || overviewRes?.recent_activities || [];
      const healthObj = healthRes || overviewRes?.systemHealth || overviewRes?.system_health || null;
      const errorsArr = Array.isArray(errorsRes) ? errorsRes : overviewRes?.recentErrors || [];

      set({
        metrics: metricsObj,
        providerStatus: provStatus,
        systemHealth: healthObj,
        recentErrors: errorsArr,
        recentActivities: activitiesArr,
        isLoading: false,
        error: null,
      });
    } catch (err: unknown) {
      const msg = err && typeof err === 'object' && 'message' in err ? String((err as { message?: string }).message) : 'Failed to connect to backend server.';
      set({
        isLoading: false,
        error: msg,
      });
    }
  },

  /** Lightweight fetch — only updates providerStatus, no loading flash */
  pollProviderStatus: async () => {
    try {
      const data = await dashboardService.getActiveProvider();
      // The enriched endpoint now returns active_provider (display name) and active_model directly
      const activeProvider: string = data?.active_provider || data?.current_provider || '';
      const activeModel: string = data?.active_model || '';
      if (!activeProvider) return;

      const current = get().providerStatus;
      const currentName = (current?.active_provider || current?.activeProvider || '').toLowerCase();

      // Only update state if the provider actually changed to avoid unnecessary re-renders
      if (currentName !== activeProvider.toLowerCase()) {
        set((state) => ({
          providerStatus: {
            ...state.providerStatus,
            active_provider: activeProvider,
            activeProvider: activeProvider,
            active_model: activeModel,
            activeModel: activeModel,
            fallbackActive: data?.fallback_active === 'true',
          },
        }));
      }
    } catch {
      // Silently ignore poll errors — don't disrupt the UI
    }
  },

  startProviderPolling: () => {
    // Clear any existing timer
    if (_providerPollTimer) clearInterval(_providerPollTimer);
    // Poll every 10 seconds
    _providerPollTimer = setInterval(() => {
      useDashboardStore.getState().pollProviderStatus();
    }, 10_000);
  },

  stopProviderPolling: () => {
    if (_providerPollTimer) {
      clearInterval(_providerPollTimer);
      _providerPollTimer = null;
    }
  },
}));

