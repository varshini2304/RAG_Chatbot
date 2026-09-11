import { apiClient } from '../axios';

export const providerService = {
  getProvidersList: async () => {
    const response = await apiClient.get('/providers');
    if (response.data && response.data.success && response.data.data) {
      return response.data.data.providers || response.data.data;
    }
    return response.data;
  }
};
