import { apiClient } from '../axios';

export const userService = {
  getProfile: async () => {
    const response = await apiClient.get('/users/me');
    if (response.data && response.data.success && response.data.data) {
      return response.data.data;
    }
    return response.data;
  },

  getUsersList: async () => {
    const response = await apiClient.get('/users');
    if (response.data && response.data.success && response.data.data) {
      return response.data.data;
    }
    return response.data;
  },

  getRolesList: async () => {
    const response = await apiClient.get('/roles');
    if (response.data && response.data.success && response.data.data) {
      return response.data.data;
    }
    return response.data;
  },

  getApiKeys: async () => {
    const response = await apiClient.get('/apikeys');
    if (response.data && response.data.success && response.data.data) {
      return response.data.data;
    }
    return response.data;
  }
};
