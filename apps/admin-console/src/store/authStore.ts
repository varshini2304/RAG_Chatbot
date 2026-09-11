import { create } from 'zustand';

interface User {
  username: string;
  email: string | null;
  role: string;
  avatarLetter: string;
}

interface AuthState {
  isAuthenticated: boolean;
  isVerifying: boolean;
  user: User | null;
  token: string | null;
  login: (username: string, password: string) => Promise<{ success: boolean; message: string }>;
  fetchProfile: () => Promise<void>;
  verifyAuth: () => Promise<void>;
  logout: () => void;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

// Clear obviously stale prototype tokens on module load
const initialToken = localStorage.getItem('token');
if (!initialToken || initialToken.startsWith('bearer_token_')) {
  localStorage.removeItem('is_auth');
  localStorage.removeItem('user');
  localStorage.removeItem('token');
}

const storedToken = localStorage.getItem('token');
const storedIsAuth = localStorage.getItem('is_auth') === 'true';
const storedUser = localStorage.getItem('user');

export const useAuthStore = create<AuthState>((set) => ({
  // Assume authenticated if localStorage says so — verifyAuth() will confirm on mount
  isAuthenticated: storedIsAuth && Boolean(storedToken),
  isVerifying: storedIsAuth && Boolean(storedToken), // show loading until verified
  user: storedIsAuth && storedUser ? JSON.parse(storedUser) : null,
  token: storedIsAuth ? storedToken : null,

  verifyAuth: async () => {
    const token = localStorage.getItem('token');
    if (!token) {
      set({ isAuthenticated: false, isVerifying: false, user: null, token: null });
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        // Token is valid — keep existing auth state
        set({ isVerifying: false });
      } else {
        // Token rejected by server
        localStorage.removeItem('is_auth');
        localStorage.removeItem('user');
        localStorage.removeItem('token');
        set({ isAuthenticated: false, isVerifying: false, user: null, token: null });
      }
    } catch {
      // Network error: backend is down — clear auth to force re-login
      localStorage.removeItem('is_auth');
      localStorage.removeItem('user');
      localStorage.removeItem('token');
      set({ isAuthenticated: false, isVerifying: false, user: null, token: null });
    }
  },

  fetchProfile: async () => {
    const stored = localStorage.getItem('user');
    if (stored) {
      try {
        set({ user: JSON.parse(stored) });
      } catch {
        // ignore parse errors
      }
    }
  },

  login: async (username: string, password: string) => {
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username.trim(), password }),
      });

      const data = await res.json() as {
        success: boolean;
        token?: string;
        username?: string;
        role?: string;
        avatar_letter?: string;
        message?: string;
      };

      if (!res.ok || !data.success) {
        return { success: false, message: data.message || 'Invalid username or password.' };
      }

      const userObj: User = {
        username: data.username ?? username,
        email: null,
        role: data.role ?? 'User',
        avatarLetter: data.avatar_letter ?? username[0].toUpperCase(),
      };

      localStorage.setItem('is_auth', 'true');
      localStorage.setItem('user', JSON.stringify(userObj));
      localStorage.setItem('token', data.token ?? '');

      set({ isAuthenticated: true, isVerifying: false, user: userObj, token: data.token ?? '' });
      return { success: true, message: 'Login successful' };
    } catch {
      return { success: false, message: 'Unable to reach the server. Please check that the API is running.' };
    }
  },

  logout: () => {
    localStorage.removeItem('is_auth');
    localStorage.removeItem('user');
    localStorage.removeItem('token');
    set({ isAuthenticated: false, isVerifying: false, user: null, token: null });
  },
}));

