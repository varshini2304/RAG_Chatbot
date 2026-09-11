import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { AuthGuard } from '../../../app/guards/AuthGuard';
import { useAuthStore } from '../../../store/authStore';

describe('AuthGuard Unit Component Tests', () => {
  it('renders children when authenticated', () => {
    useAuthStore.setState({
      isAuthenticated: true,
      isVerifying: false,
      verifyAuth: async () => {},
    });

    render(
      <MemoryRouter initialEntries={['/protected']}>
        <Routes>
          <Route
            path="/protected"
            element={
              <AuthGuard>
                <div>Protected Dashboard</div>
              </AuthGuard>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('Protected Dashboard')).toBeInTheDocument();
  });

  it('redirects to /login when unauthenticated', () => {
    useAuthStore.setState({
      isAuthenticated: false,
      isVerifying: false,
      verifyAuth: async () => {},
    });

    render(
      <MemoryRouter initialEntries={['/protected']}>
        <Routes>
          <Route
            path="/protected"
            element={
              <AuthGuard>
                <div>Protected Dashboard</div>
              </AuthGuard>
            }
          />
          <Route path="/login" element={<div>Login Screen</div>} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.queryByText('Protected Dashboard')).not.toBeInTheDocument();
    expect(screen.getByText('Login Screen')).toBeInTheDocument();
  });
});
