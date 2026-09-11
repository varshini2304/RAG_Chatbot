import { apiClient } from '../axios';

export const settingsService = {
  getGeneralSettings: async () => {
    const response = await apiClient.get('/settings');
    if (response.data && response.data.success && response.data.data) {
      return response.data.data;
    }
    return response.data;
  },

  updateSettings: async (settingsData: Record<string, unknown>) => {
    const response = await apiClient.put('/settings', settingsData);
    return response.data;
  },

  getIntegrations: async () => {
    const response = await apiClient.get('/settings/integrations');
    if (response.data && response.data.success && response.data.data) {
      return response.data.data;
    }
    return response.data;
  }
};
