import { describe, it, expect } from 'vitest';
import { settingsService } from '../../../services/api/settingsService';
import { http, HttpResponse } from 'msw';
import { server } from '../../mocks/server';

describe('settingsService Unit Tests', () => {
  it('should fetch general settings from API', async () => {
    const data = await settingsService.getGeneralSettings();

    expect(data).toBeDefined();
    expect(data.appName).toBe('RAG Admin Console');
    expect(data.sessionTimeout).toBe('30m');
    expect(data.allowedFileTypes).toEqual(['pdf', 'txt', 'docx', 'md', 'csv']);
  });

  it('should send updated settings payload to API', async () => {
    const updatePayload = {
      appName: 'Custom RAG Platform',
      sessionTimeout: '60m',
      systemLogLevel: 'Debug',
      allowedFileTypes: ['pdf', 'txt'],
    };

    const res = await settingsService.updateSettings(updatePayload);
    expect(res.success).toBe(true);
    expect(res.data.appName).toBe('Custom RAG Platform');
  });

  it('should fetch integrations list from API', async () => {
    server.use(
      http.get('http://localhost:8000/api/v1/settings/integrations', () => {
        return HttpResponse.json({
          success: true,
          data: [
            { name: 'Confluence Portal', status: 'Active', lastSync: '10m ago' },
          ],
        });
      })
    );

    const integrations = await settingsService.getIntegrations();
    expect(integrations).toHaveLength(1);
    expect(integrations[0].name).toBe('Confluence Portal');
  });
});
