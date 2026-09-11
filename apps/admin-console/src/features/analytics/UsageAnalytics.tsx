import React, { useEffect } from 'react';
import { ChartCard } from '../../shared/components/ChartCard';
import { BarChart3, RefreshCw } from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import { useAnalyticsStore } from '../../store/analyticsStore';
import { useDashboardStore } from '../../store/dashboardStore';

export const UsageAnalytics: React.FC = () => {
  const { trendData, fetchAnalyticsData } = useAnalyticsStore();
  const { metrics, fetchDashboardData } = useDashboardStore();

  useEffect(() => {
    fetchAnalyticsData();
    fetchDashboardData();
  }, [fetchAnalyticsData, fetchDashboardData]);

  const totalConvVal = metrics?.total_conversations?.value ?? '0';
  const queriesPerDayVal = metrics?.queries_per_day?.value ?? '0';

  return (
    <div className="space-y-6">
      <div className="p-5 bg-[#161B2E] border border-white/[0.06] rounded-[18px] flex items-center justify-between">
        <div className="space-y-1">
          <h2 className="text-sm font-extrabold text-[#F8FAFC] tracking-wider uppercase">Usage & Conversation Analytics</h2>
          <p className="text-xs text-[#94A3B8]">Analyze conversational loads, daily user request spikes, and RAG volume stats from backend APIs.</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              fetchAnalyticsData();
              fetchDashboardData();
            }}
            className="flex items-center gap-1.5 px-3.5 py-1.5 bg-[#6D5DF6]/20 border border-[#6D5DF6]/40 rounded-[12px] text-xs font-bold text-white hover:bg-[#6D5DF6]/30 transition-all cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>
          <div className="w-9 h-9 rounded-xl bg-[#6D5DF6]/15 text-[#6D5DF6] flex items-center justify-center flex-shrink-0">
            <BarChart3 className="w-5 h-5" />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Request volume bar chart */}
        <ChartCard title="Daily Request Volume">
          {trendData.length === 0 ? (
            <div className="flex h-full items-center justify-center text-xs text-[#94A3B8]">
              No historical request trends collected in backend metric store.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={trendData} margin={{ top: 15, right: 15, left: -15, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.05)" />
                <XAxis dataKey="date" stroke="#94A3B8" fontSize={11} tickLine={false} />
                <YAxis stroke="#94A3B8" fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{ background: '#161B2E', borderColor: 'rgba(255, 255, 255, 0.1)', borderRadius: '14px', fontSize: '12px' }}
                  labelStyle={{ fontWeight: 'bold', color: '#F8FAFC' }}
                />
                <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: '11px' }} />
                <Bar dataKey="conversations" name="Total Queries" fill="#6D5DF6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        {/* Active conversation sessions */}
        <ChartCard title="User Session Spikes">
          {trendData.length === 0 ? (
            <div className="flex h-full items-center justify-center text-xs text-[#94A3B8]">
              No historical session trend data available.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={trendData} margin={{ top: 15, right: 15, left: -15, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.05)" />
                <XAxis dataKey="date" stroke="#94A3B8" fontSize={11} tickLine={false} />
                <YAxis stroke="#94A3B8" fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{ background: '#161B2E', borderColor: 'rgba(255, 255, 255, 0.1)', borderRadius: '14px', fontSize: '12px' }}
                  labelStyle={{ fontWeight: 'bold', color: '#F8FAFC' }}
                />
                <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: '11px' }} />
                <Bar dataKey="conversations" name="Active Sessions" fill="#A855F7" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>
      </div>

      {/* Aggregated totals */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <div className="enterprise-card p-5 space-y-2 bg-[#161B2E] border border-white/[0.06] rounded-[18px]">
          <span className="text-xs font-bold text-[#94A3B8] uppercase tracking-wider">Total Stored Conversations</span>
          <p className="font-outfit text-3xl font-black text-[#F8FAFC] leading-none">{totalConvVal}</p>
          <span className="text-xs text-[#6D5DF6] font-semibold block">Queried from backend chat storage</span>
        </div>

        <div className="enterprise-card p-5 space-y-2 bg-[#161B2E] border border-white/[0.06] rounded-[18px]">
          <span className="text-xs font-bold text-[#94A3B8] uppercase tracking-wider">Average Daily Queries</span>
          <p className="font-outfit text-3xl font-black text-[#F8FAFC] leading-none">{queriesPerDayVal}</p>
          <span className="text-xs text-[#6D5DF6] font-semibold block">Queries per day metric</span>
        </div>
      </div>
    </div>
  );
};
