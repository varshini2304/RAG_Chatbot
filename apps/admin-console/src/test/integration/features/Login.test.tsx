import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { Login } from '../../../features/authentication/Login';

describe('Login Feature Integration Tests', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('renders login form with username and password fields', () => {
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    );

    expect(screen.getByText('RAG Admin Console')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Enter your username')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Enter your password')).toBeInTheDocument();
  });

  it('shows error validation when submitting empty username', async () => {
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    );

    const submitBtn = screen.getByRole('button', { name: /sign in/i });
    fireEvent.click(submitBtn);

    expect(await screen.findByText('Username is required.')).toBeInTheDocument();
  });

  it('navigates to dashboard on successful login', async () => {
    vi.spyOn(global, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        token: 'test_token',
        username: 'admin',
        role: 'Administrator',
        avatar_letter: 'A',
      }),
    } as Response);

    render(
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/dashboard" element={<div>Dashboard Overview Page</div>} />
        </Routes>
      </MemoryRouter>
    );

    const userInput = screen.getByPlaceholderText('Enter your username');
    const passInput = screen.getByPlaceholderText('Enter your password');
    const submitBtn = screen.getByRole('button', { name: /sign in/i });

    fireEvent.change(userInput, { target: { value: 'admin' } });
    fireEvent.change(passInput, { target: { value: 'admin123' } });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText('Dashboard Overview Page')).toBeInTheDocument();
    });
  });
});
