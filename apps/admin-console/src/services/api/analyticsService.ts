import { apiClient } from '../axios';

export const analyticsService = {
  getAnalyticsData: async () => {
    const response = await apiClient.get('/analytics');
    if (response.data && response.data.success && response.data.data) {
      return {
        trendData: response.data.data.trend_data || [],
        providerShares: response.data.data.provider_shares || [],
      };
    }
    return response.data;
  }
};
