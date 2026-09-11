import React, { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useDashboardStore } from '../../store/dashboardStore';
import { useAnalyticsStore } from '../../store/analyticsStore';
import { MetricCard } from '../../shared/components/MetricCard';
import { ChartCard } from '../../shared/components/ChartCard';
import {
  MessageSquare,
  Users,
  Zap,
  CircleAlert,
  Clock,
  Cpu,
  ArrowRight,
  FileText,
  RefreshCw,
  AlertTriangle,
  XCircle
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  PieChart,
  Pie,
  Cell
} from 'recharts';

export const Dashboard: React.FC = () => {
  const { metrics, providerStatus, recentErrors, recentActivities, error, fetchDashboardData, startProviderPolling, stopProviderPolling } = useDashboardStore();
  const { trendData, providerShares, fetchAnalyticsData } = useAnalyticsStore();

  useEffect(() => {
    fetchDashboardData();
    fetchAnalyticsData();
    // Start live polling for active provider every 10 seconds
    startProviderPolling();
    return () => {
      stopProviderPolling();
    };
  }, [fetchDashboardData, fetchAnalyticsData, startProviderPolling, stopProviderPolling]);

  const totalConversationsVal = (providerShares || []).reduce((acc, curr) => acc + (curr.value || 0), 0);

  const getMetric = (key: string, defaultTitle: string, defaultValue: string) => {
    if (metrics && metrics[key]) {
      return metrics[key];
    }
    return {
      title: defaultTitle,
      value: defaultValue,
      change: '—',
      trend: 'up' as const,
    };
  };

  const totalConvMetric = getMetric('total_conversations', 'Total Conversations', '0');
  const activeUsersMetric = getMetric('active_users', 'Active Users', '0');
  const queriesPerDayMetric = getMetric('queries_per_day', 'Queries / Day', '0');
  const errorRateMetric = getMetric('error_rate', 'Error Rate', '0.00%');
  const avgResponseTimeMetric = getMetric('avg_response_time', 'Avg. Response Time', '0.00s');

  const displayErrors = recentErrors || [];

  const handleRefresh = () => {
    fetchDashboardData();
    fetchAnalyticsData();
  };

  const getLevelClasses = (level?: string) => {
    const normalized = (level || '').toUpperCase();
    if (normalized === 'ERROR') return 'bg-[#EF4444]/15 text-[#EF4444] border border-[#EF4444]/30';
    if (normalized === 'WARNING') return 'bg-[#F59E0B]/15 text-[#F59E0B] border border-[#F59E0B]/30';
    return 'bg-[#94A3B8]/15 text-[#94A3B8] border border-[#94A3B8]/30';
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-outfit text-2xl font-black tracking-tight text-[#F8FAFC]">Executive Dashboard</h2>
          <p className="mt-0.5 text-xs text-[#94A3B8]">Real-time system operational metrics & LLM provider health</p>
        </div>
        <button
          onClick={handleRefresh}
          className="flex cursor-pointer items-center gap-2 rounded-[14px] border border-[#6D5DF6]/30 bg-[#6D5DF6]/15 px-4 py-2 text-xs font-extrabold text-[#6D5DF6] shadow-sm transition-all hover:bg-[#6D5DF6]/25 active:scale-95"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          <span>Refresh Telemetry</span>
        </button>
      </div>

      {error && (
        <div className="flex items-center justify-between rounded-[18px] border border-red-500/30 bg-red-900/20 p-4 text-xs text-red-300">
          <div className="flex items-center gap-2.5">
            <AlertTriangle className="h-4.5 w-4.5 flex-shrink-0 text-[#EF4444]" />
            <span>Backend connection notice: {error}</span>
          </div>
          <button
            onClick={() => {
              fetchDashboardData();
              fetchAnalyticsData();
            }}
            className="flex cursor-pointer items-center gap-1.5 rounded-[14px] border border-red-500/40 bg-red-500/20 px-3 py-1.5 text-xs font-bold text-white transition-all hover:bg-red-500/30"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Retry API</span>
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2 lg:grid-cols-5 xl:gap-4">
        <MetricCard title={totalConvMetric.title} value={totalConvMetric.value} icon={MessageSquare} iconBg="bg-[#6D5DF6]/15" iconColor="text-[#6D5DF6]" />
        <MetricCard title={activeUsersMetric.title} value={activeUsersMetric.value} icon={Users} iconBg="bg-[#3B82F6]/15" iconColor="text-[#3B82F6]" />
        <MetricCard title={queriesPerDayMetric.title} value={queriesPerDayMetric.value} icon={Zap} iconBg="bg-[#F59E0B]/15" iconColor="text-[#F59E0B]" />
        <MetricCard title={errorRateMetric.title} value={errorRateMetric.value} icon={CircleAlert} iconBg="bg-[#EF4444]/15" iconColor="text-[#EF4444]" />
        <MetricCard title={avgResponseTimeMetric.title} value={avgResponseTimeMetric.value} icon={Clock} iconBg="bg-[#14B8A6]/15" iconColor="text-[#14B8A6]" />
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <ChartCard title="Conversations Trend">
          {trendData && trendData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData} margin={{ top: 15, right: 15, left: -10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.05)" />
                <XAxis dataKey="date" stroke="#94A3B8" fontSize={11} tickLine={false} />
                <YAxis stroke="#94A3B8" fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{ background: '#161B2E', borderColor: 'rgba(255, 255, 255, 0.1)', borderRadius: '14px', fontSize: '12px' }}
                  labelStyle={{ fontWeight: 'bold', color: '#F8FAFC' }}
                />
                <Line type="monotone" dataKey="conversations" stroke="#6D5DF6" strokeWidth={3} dot={{ r: 4, fill: '#6D5DF6' }} activeDot={{ r: 6 }} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-full items-center justify-center text-xs text-[#94A3B8]">No conversation trend telemetry recorded yet.</div>
          )}
        </ChartCard>

        <ChartCard title="Provider Usage">
          {providerShares && providerShares.length > 0 ? (
            <div className="flex h-full items-center justify-between px-2 py-1">
              <div className="relative flex h-36 w-36 flex-shrink-0 items-center justify-center">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
                    <Pie data={providerShares} cx="50%" cy="50%" innerRadius={42} outerRadius={60} paddingAngle={3} dataKey="value">
                      {providerShares.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color || '#6D5DF6'} />
                      ))}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
                <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
                  <span className="text-[9px] font-bold uppercase tracking-wider text-[#94A3B8]">Total</span>
                  <span className="mt-0.5 font-outfit text-sm font-black text-[#F8FAFC]">
                    {totalConversationsVal > 0 ? totalConversationsVal.toLocaleString() : '1'}
                  </span>
                </div>
              </div>

              <div className="ml-4 flex-1 space-y-3">
                {providerShares.map((provider) => (
                  <div key={provider.name} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <span className="h-3 w-3 flex-shrink-0 rounded-full shadow-sm" style={{ backgroundColor: provider.color || '#6D5DF6' }} />
                      <span className="font-bold text-[#F8FAFC]">{provider.name}</span>
                    </div>
                    <span className="font-black text-[#F8FAFC]">{provider.percentage || `${provider.share_pct || 0}%`}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="flex h-full items-center justify-center text-xs text-[#94A3B8]">No provider telemetry recorded yet.</div>
          )}
        </ChartCard>

        <ChartCard title="Response Time (s)">
          {trendData && trendData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData} margin={{ top: 15, right: 15, left: -10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.05)" />
                <XAxis dataKey="date" stroke="#94A3B8" fontSize={11} tickLine={false} />
                <YAxis stroke="#94A3B8" fontSize={11} tickLine={false} domain={[0, 'auto']} allowDecimals tickFormatter={(val) => `${Number(val).toFixed(1)}`} />
                <Tooltip
                  contentStyle={{ background: '#161B2E', borderColor: 'rgba(255, 255, 255, 0.1)', borderRadius: '14px', fontSize: '12px' }}
                  labelStyle={{ fontWeight: 'bold', color: '#F8FAFC' }}
                  formatter={(val: unknown) => [`${Number(val || 0).toFixed(2)}s`, 'Response Time']}
                />
                <Line type="monotone" dataKey="responseTime" stroke="#3B82F6" strokeWidth={3} dot={{ r: 4, fill: '#3B82F6' }} activeDot={{ r: 6 }} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-full items-center justify-center text-xs text-[#94A3B8]">No response latency telemetry recorded yet.</div>
          )}
        </ChartCard>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <div className="enterprise-card flex flex-col justify-between rounded-[18px] border border-white/[0.06] bg-[#161B2E] p-5">
          <div>
            <div className="mb-3 flex items-center justify-between">
              <h3 className="font-outfit text-[18px] font-bold tracking-tight text-[#F8FAFC]">Recent Errors & Failures</h3>
              <Link to="/monitoring/errors" className="text-xs font-bold text-[#6D5DF6] hover:underline">View All</Link>
            </div>

            {displayErrors && displayErrors.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-left">
                  <thead>
                    <tr className="border-b border-white/[0.06] text-[11px] font-bold uppercase tracking-wider text-[#94A3B8]">
                      <th className="py-2 font-bold">Timestamp</th>
                      <th className="py-2 font-bold">Level</th>
                      <th className="py-2 font-bold">Module</th>
                      <th className="py-2 font-bold">Message</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/[0.04] text-xs">
                    {displayErrors.slice(0, 5).map((err, idx) => (
                      <tr key={err.id || idx} className="transition-colors hover:bg-white/[0.02]">
                        <td className="whitespace-nowrap py-2.5">
                          <div className="flex items-center gap-1.5">
                            <XCircle className={`h-4 w-4 flex-shrink-0 ${(err.level || '').toUpperCase() === 'WARNING' ? 'text-[#F59E0B]' : 'text-[#EF4444]'}`} />
                            <span className="font-semibold text-[#F8FAFC]">{err.timestamp || err.time}</span>
                          </div>
                        </td>
                        <td className="whitespace-nowrap py-2.5">
                          <span className={`rounded px-2 py-0.5 text-[11px] font-bold ${getLevelClasses(err.level)}`}>
                            {err.level || 'ERROR'}
                          </span>
                        </td>
                        <td className="whitespace-nowrap py-2.5 font-mono text-[11px] text-[#94A3B8]">{err.module || 'app.llm'}</td>
                        <td className="max-w-[220px] truncate py-2.5 font-mono text-[11px] text-[#F8FAFC]" title={err.message || err.detail}>
                          {err.message || err.detail || '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="rounded-xl border border-white/[0.04] bg-[#0B1020]/50 p-4 py-10 text-center text-xs font-semibold text-[#22C55E]">
                No chatbot warning, error, or failover logs recorded.
              </div>
            )}
          </div>
        </div>

        <div className="enterprise-card flex flex-col justify-between rounded-[18px] border border-white/[0.06] bg-[#161B2E] p-5">
          <div>
            <h3 className="mb-4 font-outfit text-[18px] font-bold tracking-tight text-[#F8FAFC]">Active Provider</h3>

            {!providerStatus ? (
              <div className="rounded-[14px] border border-white/[0.04] bg-[#0B1020]/50 py-10 text-center text-xs font-semibold text-[#94A3B8]">
                <div className="flex items-center justify-center gap-2">
                  <RefreshCw className="h-4 w-4 animate-spin text-[#6D5DF6]" />
                  <span>Connecting to backend telemetry...</span>
                </div>
              </div>
            ) : (() => {
              const activeP = providerStatus.activeProvider || providerStatus.active_provider || 'Ollama Server';
              const isOllama = activeP.toLowerCase().includes('ollama');
              const isGemini = activeP.toLowerCase().includes('gemini');
              const modelName = providerStatus.activeModel || providerStatus.active_model || (isOllama ? 'qwen2.5:3b' : isGemini ? 'gemini-2.5-flash' : 'llama-3.3-70b-versatile');
              const pillBg = isOllama ? 'bg-[#F59E0B]/15 text-[#F59E0B] border-[#F59E0B]/30' : isGemini ? 'bg-[#3B82F6]/15 text-[#3B82F6] border-[#3B82F6]/30' : 'bg-[#6D5DF6]/15 text-[#6D5DF6] border-[#6D5DF6]/30';

              return (
                <>
                  <div className="mb-4 flex items-center gap-3.5 rounded-[14px] border border-white/[0.06] bg-[#0B1020] p-4">
                    <div className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-[14px] border shadow-md ${pillBg}`}>
                      <Cpu className="h-5 w-5" />
                    </div>
                    <div className="flex min-w-0 flex-grow flex-col">
                      <div className="flex items-center gap-2">
                        <span className="font-outfit text-base font-extrabold text-[#F8FAFC]">{activeP}</span>
                        <span className="rounded-full border border-[#22C55E]/30 bg-[#22C55E]/15 px-2.5 py-0.5 text-[10px] font-black uppercase tracking-wider text-[#22C55E]">Active</span>
                      </div>
                      <span className="mt-0.5 text-xs text-[#94A3B8]">Model: {modelName}</span>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-2 rounded-[14px] border border-white/[0.06] bg-[#0D1322] p-3.5 text-center">
                    <div>
                      <span className="block text-[10px] font-bold uppercase tracking-wider text-[#94A3B8]">Latency</span>
                      <span className="mt-0.5 block font-outfit text-sm font-black text-[#F8FAFC]">{avgResponseTimeMetric.value}</span>
                    </div>
                    <div>
                      <span className="block text-[10px] font-bold uppercase tracking-wider text-[#94A3B8]">Requests</span>
                      <span className="mt-0.5 block font-outfit text-sm font-black text-[#F8FAFC]">{totalConversationsVal > 0 ? totalConversationsVal : 1}</span>
                    </div>
                    <div>
                      <span className="block text-[10px] font-bold uppercase tracking-wider text-[#94A3B8]">Success Rate</span>
                      <span className="mt-0.5 block font-outfit text-sm font-black text-[#22C55E]">100%</span>
                    </div>
                  </div>
                </>
              );
            })()}
          </div>

          <Link to="/settings/providers" className="mt-4 flex items-center gap-1.5 text-xs font-bold text-[#6D5DF6] hover:text-[#5b4be0]">
            <span>View All Providers</span>
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>

        <div className="enterprise-card flex flex-col justify-between rounded-[18px] border border-white/[0.06] bg-[#161B2E] p-5">
          <div>
            <div className="mb-4 flex items-center justify-between">
              <h3 className="font-outfit text-[18px] font-bold tracking-tight text-[#F8FAFC]">Recent Activity</h3>
              <Link to="/monitoring/logs" className="text-xs font-bold text-[#6D5DF6] hover:underline">View All</Link>
            </div>

            <div className="space-y-3.5">
              {recentActivities && recentActivities.length > 0 ? (
                recentActivities.slice(0, 5).map((act, idx) => (
                  <div key={act.id || idx} className="rounded-xl p-1 transition-colors hover:bg-white/[0.02]">
                    <div className="flex items-start gap-3">
                      <div className="mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-xl bg-[#6D5DF6]/15 text-[#6D5DF6] shadow-sm">
                        <FileText className="h-4 w-4" />
                      </div>
                      <div className="flex min-w-0 flex-grow flex-col">
                        <span className="truncate text-xs font-bold text-[#F8FAFC]">{act.title || act.description}</span>
                        <span className="mt-0.5 text-[11px] text-[#94A3B8]">{act.timestamp || act.time}</span>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="py-10 text-center text-xs text-[#94A3B8]">No recent system activity recorded yet.</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
