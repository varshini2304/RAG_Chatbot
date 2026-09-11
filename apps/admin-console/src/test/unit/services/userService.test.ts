import { describe, it, expect } from 'vitest';
import { userService } from '../../../services/api/userService';

describe('userService Unit Tests', () => {
  it('should fetch user profile (/me)', async () => {
    const profile = await userService.getProfile();
    expect(profile).toBeDefined();
    expect(profile.username).toBe('admin');
    expect(profile.role).toBe('Administrator');
  });

  it('should fetch users list', async () => {
    const users = await userService.getUsersList();
    expect(Array.isArray(users)).toBe(true);
    expect(users).toHaveLength(2);
    expect(users[0].name).toBe('Admin User');
  });

  it('should fetch roles list', async () => {
    const roles = await userService.getRolesList();
    expect(Array.isArray(roles)).toBe(true);
    expect(roles).toHaveLength(2);
    expect(roles[0].name).toBe('Administrator');
  });

  it('should fetch API keys', async () => {
    const apiKeys = await userService.getApiKeys();
    expect(Array.isArray(apiKeys)).toBe(true);
    expect(apiKeys).toHaveLength(1);
    expect(apiKeys[0].name).toBe('Production Gateway');
  });
});
