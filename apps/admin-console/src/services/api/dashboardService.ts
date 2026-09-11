import { apiClient } from '../axios';

export const dashboardService = {
  getOverviewMetrics: async () => {
    const response = await apiClient.get('/dashboard/overview');
    if (response.data && response.data.success && response.data.data) {
      return response.data.data;
    }
    return response.data;
  },

  getRecentErrors: async () => {
    const response = await apiClient.get('/monitoring/errors');
    if (response.data && response.data.success && response.data.data) {
      return response.data.data;
    }
    return response.data;
  },

  getSystemHealth: async () => {
    const response = await apiClient.get('/dashboard/system-health');
    if (response.data && response.data.success && response.data.data) {
      return response.data.data;
    }
    return response.data;
  },

  /** Lightweight poll — returns live active provider info from the LLM router */
  getActiveProvider: async () => {
    const response = await apiClient.get('/providers/current');
    if (response.data && response.data.success && response.data.data) {
      return response.data.data;
    }
    return response.data;
  },
};

