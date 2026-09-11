import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Users } from '../../../features/users/Users';
import { http, HttpResponse } from 'msw';
import { server } from '../../mocks/server';

describe('Users Feature Integration Tests', () => {
  it('renders registered user accounts list from backend API', async () => {
    render(<Users />);

    expect(await screen.findByText('Admin User')).toBeInTheDocument();
    expect(screen.getByText('admin@company.com')).toBeInTheDocument();
    expect(screen.getByText('Analyst User')).toBeInTheDocument();
  });

  it('triggers user list refresh when Refresh button clicked', async () => {
    render(<Users />);

    const refreshBtn = await screen.findByRole('button', { name: /refresh/i });
    fireEvent.click(refreshBtn);
  });

  it('renders empty users table state when backend returns no records', async () => {
    server.use(
      http.get('http://localhost:8000/api/v1/users', () => {
        return HttpResponse.json({ success: true, data: [] });
      })
    );

    render(<Users />);

    await waitFor(() => {
      expect(screen.getByText('No registered user accounts found.')).toBeInTheDocument();
    });
  });
});
