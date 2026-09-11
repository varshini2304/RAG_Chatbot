/**
 * Centralized API client wrapper using standard browser `fetch`.
 * Handles base URL, Authorization Bearer header, JSON & multipart payloads,
 * response unwrapping, and 401 unauthorized token clearing.
 */

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string) || 'http://localhost:8000/api/v1';

const TOKEN_KEY = 'user_portal_jwt_token';

export const tokenStorage = {
  get: (): string | null => localStorage.getItem(TOKEN_KEY),
  set: (token: string): void => localStorage.setItem(TOKEN_KEY, token),
  clear: (): void => localStorage.removeItem(TOKEN_KEY),
};

export class ApiError extends Error {
  status: number;
  errors: string[];

  constructor(message: string, status: number, errors: string[] = []) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.errors = errors;
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const token = tokenStorage.get();

  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Set default Content-Type to json if body is present and not FormData
  if (options.body && !(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  const config: RequestInit = {
    ...options,
    headers,
  };

  let response: Response;
  try {
    response = await fetch(url, config);
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Network failure';
    throw new ApiError(`Network error: ${msg}`, 0, [msg]);
  }

  // Automatic 401 handling — clear token on unauthorized
  if (response.status === 401) {
    tokenStorage.clear();
  }

  let data: Record<string, unknown> | null;
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    data = (await response.json()) as Record<string, unknown>;
  } else {
    data = { message: await response.text() };
  }

  if (!response.ok) {
    const errorMsg = (data?.message as string) || (data?.detail as string) || `HTTP Error ${response.status}`;
    const errorsList = (data?.errors as string[]) || (Array.isArray(data?.detail) ? (data.detail as Array<{ msg?: string }>).map((d) => d.msg || '') : [errorMsg]);
    throw new ApiError(errorMsg, response.status, errorsList);
  }

  return data as T;
}

export const api = {
  get: <T>(endpoint: string, headers?: Record<string, string>) =>
    request<T>(endpoint, { method: 'GET', headers }),

  post: <T>(endpoint: string, body?: unknown, headers?: Record<string, string>) =>
    request<T>(endpoint, {
      method: 'POST',
      body: body instanceof FormData ? body : JSON.stringify(body),
      headers,
    }),

  put: <T>(endpoint: string, body?: unknown, headers?: Record<string, string>) =>
    request<T>(endpoint, {
      method: 'PUT',
      body: body instanceof FormData ? body : JSON.stringify(body),
      headers,
    }),

  delete: <T>(endpoint: string, headers?: Record<string, string>) =>
    request<T>(endpoint, { method: 'DELETE', headers }),
};
