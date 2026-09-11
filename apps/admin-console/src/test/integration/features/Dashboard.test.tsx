import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Dashboard } from '../../../features/dashboard/Dashboard';
import { http, HttpResponse } from 'msw';
import { server } from '../../mocks/server';

describe('Dashboard Feature Integration Tests', () => {
  it('renders executive dashboard metrics and system telemetry', async () => {
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    );

    expect(screen.getByText('Executive Dashboard')).toBeInTheDocument();
    expect(await screen.findByText('12,450')).toBeInTheDocument();
    expect(screen.getByText('458')).toBeInTheDocument();
    expect(screen.getByText('3,210')).toBeInTheDocument();
  });

  it('triggers refresh telemetry action when button clicked', async () => {
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    );

    const refreshBtn = await screen.findByRole('button', { name: /refresh telemetry/i });
    fireEvent.click(refreshBtn);
  });

  it('renders backend error notice banner when API fails', async () => {
    server.use(
      http.get('http://localhost:8000/api/v1/dashboard/overview', () => {
        return HttpResponse.json({ message: 'Database Connection Timeout' }, { status: 500 });
      })
    );

    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Backend connection notice:/i)).toBeInTheDocument();
    });
  });
});
