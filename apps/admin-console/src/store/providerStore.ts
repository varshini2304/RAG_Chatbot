import { create } from 'zustand';
import { providerService } from '../services/api/providerService';

export interface ProviderDetail {
  id?: string;
  name: string;
  model: string;
  status: 'Online' | 'Offline' | 'Degraded' | string;
  latency: string;
  requests: number;
  failures: number;
  successRate: string;
  circuitBreakerState: 'CLOSED' | 'OPEN' | 'HALF-OPEN' | string;
  lastHealthCheck: string;
  version?: string;
}

const defaultProviders: ProviderDetail[] = [
  {
    name: 'Groq Cloud',
    model: 'llama-3.3-70b-versatile',
    status: 'Online',
    latency: '142ms',
    requests: 1240,
    failures: 0,
    successRate: '100%',
    circuitBreakerState: 'CLOSED',
    lastHealthCheck: 'Just now'
  },
  {
    name: 'Google Gemini',
    model: 'gemini-2.5-flash',
    status: 'Online',
    latency: '310ms',
    requests: 850,
    failures: 2,
    successRate: '99.8%',
    circuitBreakerState: 'CLOSED',
    lastHealthCheck: 'Just now'
  },
  {
    name: 'Ollama Server',
    model: 'qwen2.5:3b',
    status: 'Online',
    latency: '85ms',
    requests: 3100,
    failures: 0,
    successRate: '100%',
    circuitBreakerState: 'CLOSED',
    lastHealthCheck: 'Just now'
  }
];

interface ProviderState {
  providers: ProviderDetail[];
  isLoading: boolean;
  error: string | null;
  fetchProviders: () => Promise<void>;
  toggleCircuitBreaker: (name: string) => void;
}

export const useProviderStore = create<ProviderState>((set) => ({
  providers: defaultProviders,
  isLoading: false,
  error: null,

  fetchProviders: async () => {
    set({ isLoading: true, error: null });
    try {
      const data = await providerService.getProvidersList();
      if (Array.isArray(data) && data.length > 0) {
        set({
          providers: data.map((p: Record<string, unknown>) => ({
            name: String(p.name || 'Unknown Provider'),
            model: String(p.model || 'default-model'),
            status: String(p.status || 'Online'),
            latency: String(p.latency || p.latency_str || (p.latency_ms ? `${p.latency_ms}ms` : '140ms')),
            requests: typeof p.requests === 'number'
              ? p.requests
              : (Number(p.requests_total ?? p.total_requests ?? 0)),
            failures: typeof p.failures === 'number'
              ? p.failures
              : (Number(p.failures_total ?? p.failure_count ?? 0)),
            successRate: String(p.successRate || p.success_rate_pct || p.success_rate || '100%'),
            circuitBreakerState: String(p.circuitBreakerState || p.circuit_breaker_status || p.circuit_breaker_state || 'CLOSED'),
            lastHealthCheck: String(p.lastHealthCheck || p.last_health_check || 'Just now'),
          })),
          isLoading: false,
          error: null,
        });
      } else {
        set({ providers: defaultProviders, isLoading: false, error: null });
      }
    } catch (err: unknown) {
      const msg = err && typeof err === 'object' && 'message' in err ? String((err as { message?: string }).message) : 'Failed to fetch provider status from backend.';
      set({
        providers: defaultProviders,
        isLoading: false,
        error: msg,
      });
    }
  },

  toggleCircuitBreaker: (name) => {
    set((state) => ({
      providers: state.providers.map((p) =>
        p.name === name
          ? {
              ...p,
              circuitBreakerState: p.circuitBreakerState === 'CLOSED' ? 'OPEN' : 'CLOSED',
              status: p.circuitBreakerState === 'CLOSED' ? 'Degraded' : 'Online',
            }
          : p
      ),
    }));
  },
}));

