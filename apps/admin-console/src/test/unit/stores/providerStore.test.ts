import { describe, it, expect, beforeEach } from 'vitest';
import { useProviderStore } from '../../../store/providerStore';
import { http, HttpResponse } from 'msw';
import { server } from '../../mocks/server';

describe('useProviderStore Unit Tests', () => {
  beforeEach(() => {
    useProviderStore.setState({
      providers: [],
      isLoading: false,
      error: null,
    });
  });

  it('should fetch providers list successfully from API', async () => {
    await useProviderStore.getState().fetchProviders();

    const providers = useProviderStore.getState().providers;
    expect(providers).toHaveLength(3);
    expect(providers[0].name).toBe('Groq Cloud');
    expect(providers[0].requests).toBe(1240);
    expect(providers[0].status).toBe('Online');
    expect(useProviderStore.getState().isLoading).toBe(false);
  });

  it('should toggle circuit breaker state from CLOSED to OPEN and back', () => {
    useProviderStore.setState({
      providers: [
        {
          name: 'Groq Cloud',
          model: 'llama-3.3-70b',
          status: 'Online',
          latency: '100ms',
          requests: 100,
          failures: 0,
          successRate: '100%',
          circuitBreakerState: 'CLOSED',
          lastHealthCheck: 'Just now',
        },
      ],
    });

    useProviderStore.getState().toggleCircuitBreaker('Groq Cloud');

    let updated = useProviderStore.getState().providers[0];
    expect(updated.circuitBreakerState).toBe('OPEN');
    expect(updated.status).toBe('Degraded');

    useProviderStore.getState().toggleCircuitBreaker('Groq Cloud');

    updated = useProviderStore.getState().providers[0];
    expect(updated.circuitBreakerState).toBe('CLOSED');
    expect(updated.status).toBe('Online');
  });

  it('should fallback to default providers when backend returns an error', async () => {
    server.use(
      http.get('http://localhost:8000/api/v1/providers', () => {
        return HttpResponse.json({ message: 'Internal Server Error' }, { status: 500 });
      })
    );

    await useProviderStore.getState().fetchProviders();

    const providers = useProviderStore.getState().providers;
    expect(providers).toHaveLength(3); // Default fallback providers
    expect(useProviderStore.getState().error).toBeDefined();
  });
});
