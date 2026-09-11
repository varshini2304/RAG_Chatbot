import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { GeneralSettings } from '../../../features/settings/GeneralSettings';
import { http, HttpResponse } from 'msw';
import { server } from '../../mocks/server';

describe('GeneralSettings Feature Integration Tests', () => {
  it('renders general settings loaded from backend API', async () => {
    render(<GeneralSettings />);

    const appNameInput = await screen.findByDisplayValue('RAG Admin Console');
    expect(appNameInput).toBeInTheDocument();
    expect(screen.getByDisplayValue('30m')).toBeInTheDocument();
  });

  it('allows user to change application name and save settings', async () => {
    render(<GeneralSettings />);

    const appNameInput = await screen.findByDisplayValue('RAG Admin Console');
    fireEvent.change(appNameInput, { target: { value: 'Updated Enterprise RAG' } });

    expect(screen.getByDisplayValue('Updated Enterprise RAG')).toBeInTheDocument();

    const saveBtn = screen.getByRole('button', { name: /save changes/i });
    fireEvent.click(saveBtn);
  });

  it('handles API error when loading settings by using default config', async () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});

    server.use(
      http.get('http://localhost:8000/api/v1/settings', () => {
        return HttpResponse.json({ message: 'Network error' }, { status: 500 });
      })
    );

    render(<GeneralSettings />);

    // Default configuration fallback
    await waitFor(() => {
      expect(screen.getByDisplayValue('RAG Admin Console')).toBeInTheDocument();
    });

    spy.mockRestore();
  });
});

