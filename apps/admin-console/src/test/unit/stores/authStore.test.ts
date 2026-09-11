import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useAuthStore } from '../../../store/authStore';

describe('useAuthStore Unit Tests', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
    useAuthStore.setState({
      isAuthenticated: false,
      user: null,
      token: null,
    });
  });

  it('should initialize with default authentication state', () => {
    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(false);
    expect(state.user).toBeNull();
  });

  it('should login successfully and persist credentials to localStorage', async () => {
    vi.spyOn(global, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        token: 'bearer_token_admin_console',
        username: 'admin',
        role: 'Administrator',
        avatar_letter: 'A',
      }),
    } as Response);

    const result = await useAuthStore.getState().login('admin', 'admin123');

    expect(result.success).toBe(true);
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
    expect(useAuthStore.getState().user?.username).toBe('admin');
    expect(useAuthStore.getState().user?.avatarLetter).toBe('A');
    expect(localStorage.getItem('is_auth')).toBe('true');
    expect(localStorage.getItem('token')).toBe('bearer_token_admin_console');
  });

  it('should logout cleanly and clear localStorage credentials', () => {
    useAuthStore.setState({
      isAuthenticated: true,
      user: { username: 'admin', email: null, role: 'Administrator', avatarLetter: 'A' },
      token: 'bearer_token_admin_console',
    });
    localStorage.setItem('is_auth', 'true');
    localStorage.setItem('user', JSON.stringify({ username: 'admin', email: null, role: 'Administrator', avatarLetter: 'A' }));
    localStorage.setItem('token', 'bearer_token_admin_console');

    useAuthStore.getState().logout();

    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(useAuthStore.getState().user).toBeNull();
    expect(useAuthStore.getState().token).toBeNull();
    expect(localStorage.getItem('is_auth')).toBeNull();
    expect(localStorage.getItem('user')).toBeNull();
  });

  it('should fetch user profile and update user state', async () => {
    const userObj = { username: 'admin', email: null, role: 'Administrator', avatarLetter: 'A' };
    localStorage.setItem('user', JSON.stringify(userObj));

    await useAuthStore.getState().fetchProfile();

    const user = useAuthStore.getState().user;
    expect(user).not.toBeNull();
    expect(user?.username).toBe('admin');
    expect(user?.role).toBe('Administrator');
  });
});
