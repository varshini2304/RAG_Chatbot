import { api, tokenStorage } from './api';

export interface UserTokenResponse {
  success: boolean;
  token: string;
  token_type: string;
  username: string;
  avatar_letter: string;
  message: string;
}

export interface UserMeResponse {
  success: boolean;
  username: string;
  avatar_letter: string;
  message: string;
}

export const authService = {
  login: async (username: string, password: string): Promise<UserTokenResponse> => {
    const data = await api.post<UserTokenResponse>('/user-auth/login', {
      username,
      password,
    });
    if (data.token) {
      tokenStorage.set(data.token);
    }
    return data;
  },

  register: async (
    username: string,
    password: string,
    confirm_password: string
  ): Promise<UserTokenResponse> => {
    const data = await api.post<UserTokenResponse>('/user-auth/register', {
      username,
      password,
      confirm_password,
    });
    if (data.token) {
      tokenStorage.set(data.token);
    }
    return data;
  },

  me: async (): Promise<UserMeResponse> => {
    return api.get<UserMeResponse>('/user-auth/me');
  },

  logout: (): void => {
    tokenStorage.clear();
  },

  hasToken: (): boolean => {
    return Boolean(tokenStorage.get());
  },
};
