import { describe, it, expect, beforeEach } from 'vitest';
import { useDashboardStore } from '../../../store/dashboardStore';
import { http, HttpResponse } from 'msw';
import { server } from '../../mocks/server';

describe('useDashboardStore Unit Tests', () => {
  beforeEach(() => {
    useDashboardStore.setState({
      metrics: {},
      systemHealth: null,
      providerStatus: null,
      recentErrors: [],
      recentActivities: [],
      isLoading: false,
      error: null,
    });
  });

  it('should fetch dashboard data successfully', async () => {
    await useDashboardStore.getState().fetchDashboardData();

    const state = useDashboardStore.getState();
    expect(state.metrics).toBeDefined();
    expect(state.metrics['total_conversations'].value).toBe('12,450');
    expect(state.systemHealth?.api_status).toMatch(/healthy/i);
    expect(state.recentErrors.length).toBeGreaterThan(0);
    expect(state.isLoading).toBe(false);
  });

  it('should handle backend error when fetching dashboard metrics', async () => {
    server.use(
      http.get('http://localhost:8000/api/v1/dashboard/overview', () => {
        return HttpResponse.json({ message: 'Service unavailable' }, { status: 503 });
      })
    );

    await useDashboardStore.getState().fetchDashboardData();

    const state = useDashboardStore.getState();
    expect(state.error).toBeDefined();
    expect(state.isLoading).toBe(false);
  });
});
