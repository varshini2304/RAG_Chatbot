import { http, HttpResponse } from 'msw';

const API_BASE = 'http://localhost:8000/api/v1';

export const mockProviders = [
  {
    id: 'groq',
    name: 'Groq Cloud',
    model: 'llama-3.3-70b-versatile',
    status: 'Online',
    latency_str: '142ms',
    latency_ms: 142.0,
    requests_total: 1240,
    failures_total: 0,
    success_rate_pct: '100%',
    circuit_breaker_status: 'CLOSED',
    is_active: true,
    last_health_check: 'Just now',
  },
  {
    id: 'gemini',
    name: 'Google Gemini',
    model: 'gemini-2.5-flash',
    status: 'Online',
    latency_str: '310ms',
    latency_ms: 310.0,
    requests_total: 850,
    failures_total: 2,
    success_rate_pct: '99.8%',
    circuit_breaker_status: 'CLOSED',
    is_active: false,
    last_health_check: 'Just now',
  },
  {
    id: 'ollama',
    name: 'Ollama Server',
    model: 'qwen2.5:3b',
    status: 'Online',
    latency_str: '85ms',
    latency_ms: 85.0,
    requests_total: 3100,
    failures_total: 0,
    success_rate_pct: '100%',
    circuit_breaker_status: 'CLOSED',
    is_active: false,
    last_health_check: 'Just now',
  },
];

export const mockGeneralSettings = {
  appName: 'RAG Admin Console',
  sessionTimeout: '30m',
  systemLogLevel: 'Info',
  allowedFileTypes: ['pdf', 'txt', 'docx', 'md', 'csv'],
};

export const mockUsers = [
  { id: 1, name: 'Admin User', email: 'admin@company.com', role: 'Administrator', status: 'Active' },
  { id: 2, name: 'Analyst User', email: 'analyst@company.com', role: 'Analyst', status: 'Active' },
];

export const mockDashboardOverview = {
  metrics: {
    total_conversations: { title: 'Total Conversations', value: '12,450', change: '+12%', trend: 'up' },
    active_users: { title: 'Active Users', value: '458', change: '+5%', trend: 'up' },
    queries_per_day: { title: 'Queries / Day', value: '3,210', change: '+8%', trend: 'up' },
    error_rate: { title: 'Error Rate', value: '0.04%', change: '-0.01%', trend: 'down' },
    avg_response_time: { title: 'Avg Response Time', value: '0.42s', change: '-0.05s', trend: 'down' },
  },
  providerStatus: {
    activeProvider: 'Groq Cloud',
    activeModel: 'llama-3.3-70b-versatile',
    circuitBreakerStatus: 'CLOSED',
  },
  recentErrors: [
    { id: '1', timestamp: '2026-07-21 09:00', level: 'ERROR', module: 'app.llm', message: 'Rate limit hit on primary key' },
  ],
  recentActivities: [
    { id: '1', title: 'System health check completed', timestamp: '2 minutes ago' },
  ],
};

export const mockSystemHealth = {
  api_status: 'Healthy',
  chroma_db: 'Healthy',
  embedding_service: 'Healthy',
  ollama_server: 'Healthy',
  cpu_usage_pct: 35,
  memory_usage_pct: 58,
  disk_usage_pct: 42,
};

export const handlers = [
  // Providers endpoint
  http.get(`${API_BASE}/providers`, () => {
    return HttpResponse.json({
      success: true,
      data: {
        current_provider: 'groq',
        providers: mockProviders,
      },
    });
  }),

  // General Settings endpoint
  http.get(`${API_BASE}/settings`, () => {
    return HttpResponse.json({
      success: true,
      data: mockGeneralSettings,
    });
  }),

  http.put(`${API_BASE}/settings`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      success: true,
      message: 'Settings updated',
      data: body,
    });
  }),

  // Users endpoint
  http.get(`${API_BASE}/users`, () => {
    return HttpResponse.json({
      success: true,
      data: mockUsers,
    });
  }),

  http.get(`${API_BASE}/users/me`, () => {
    return HttpResponse.json({
      success: true,
      data: { username: 'admin', email: 'admin@company.com', role: 'Administrator' },
    });
  }),

  // Dashboard endpoints
  http.get(`${API_BASE}/dashboard/overview`, () => {
    return HttpResponse.json({
      success: true,
      data: mockDashboardOverview,
    });
  }),

  http.get(`${API_BASE}/dashboard/health`, () => {
    return HttpResponse.json({
      success: true,
      data: mockSystemHealth,
    });
  }),

  http.get(`${API_BASE}/dashboard/system-health`, () => {
    return HttpResponse.json({
      success: true,
      data: mockSystemHealth,
    });
  }),

  http.get(`${API_BASE}/dashboard/errors`, () => {
    return HttpResponse.json({
      success: true,
      data: mockDashboardOverview.recentErrors,
    });
  }),

  http.get(`${API_BASE}/monitoring/errors`, () => {
    return HttpResponse.json({
      success: true,
      data: mockDashboardOverview.recentErrors,
    });
  }),

  // Roles & API Keys
  http.get(`${API_BASE}/roles`, () => {
    return HttpResponse.json({
      success: true,
      data: [
        { name: 'Administrator', usersCount: 2, permissions: ['READ', 'WRITE', 'DELETE', 'ADMIN'] },
        { name: 'Viewer', usersCount: 10, permissions: ['READ'] },
      ],
    });
  }),

  http.get(`${API_BASE}/apikeys`, () => {
    return HttpResponse.json({
      success: true,
      data: [
        { id: '1', name: 'Production Gateway', key: 'rag_pk_live_xxxx', created: '2026-01-01', status: 'Active' },
      ],
    });
  }),
];
