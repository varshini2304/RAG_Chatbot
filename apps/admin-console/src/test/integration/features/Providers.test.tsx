import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Providers } from '../../../features/providers/Providers';
import { useProviderStore } from '../../../store/providerStore';
import { http, HttpResponse } from 'msw';
import { server } from '../../mocks/server';

describe('Providers Feature Integration Tests', () => {
  it('renders provider list and metrics on success', async () => {
    render(<Providers />);

    expect(await screen.findByText('Groq Cloud')).toBeInTheDocument();
    expect(screen.getByText('Google Gemini')).toBeInTheDocument();
    expect(screen.getByText('Ollama Server')).toBeInTheDocument();

    // Check rendered request numbers and latencies
    expect(screen.getByText('1,240')).toBeInTheDocument();
    expect(screen.getByText('142ms')).toBeInTheDocument();
  });

  it('allows toggling circuit breaker state', async () => {
    render(<Providers />);

    const breakerButton = await screen.findAllByRole('button', { name: /trip breaker/i });
    expect(breakerButton.length).toBeGreaterThan(0);

    fireEvent.click(breakerButton[0]);

    await waitFor(() => {
      expect(useProviderStore.getState().providers[0].circuitBreakerState).toBe('OPEN');
    });
  });

  it('handles API failure gracefully with default providers state', async () => {
    server.use(
      http.get('http://localhost:8000/api/v1/providers', () => {
        return HttpResponse.json({ message: 'Internal Server Error' }, { status: 500 });
      })
    );

    render(<Providers />);

    // Should render default providers instead of breaking
    expect(await screen.findByText('Groq Cloud')).toBeInTheDocument();
    expect(screen.getByText('Google Gemini')).toBeInTheDocument();
  });
});
