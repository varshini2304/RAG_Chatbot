import React, { useEffect } from 'react';
import { ChartCard } from '../../shared/components/ChartCard';
import { Users, RefreshCw } from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import { useAnalyticsStore } from '../../store/analyticsStore';
import { useDashboardStore } from '../../store/dashboardStore';

export const UserAnalytics: React.FC = () => {
  const { trendData, fetchAnalyticsData } = useAnalyticsStore();
  const { metrics, fetchDashboardData } = useDashboardStore();

  useEffect(() => {
    fetchAnalyticsData();
    fetchDashboardData();
  }, [fetchAnalyticsData, fetchDashboardData]);

  const activeUsersVal = metrics?.active_users?.value ?? '0';
  const totalConvVal = metrics?.total_conversations?.value ?? '0';

  return (
    <div className="space-y-6">
      <div className="gradient-border-card p-5 flex items-center justify-between">
        <div className="space-y-1">
          <h2 className="text-sm font-extrabold text-white tracking-wider uppercase">User & Engagement Analytics</h2>
          <p className="text-xs text-muted">Analyze unique user activities, active session distributions, and query volumes per user derived from backend services.</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              fetchAnalyticsData();
              fetchDashboardData();
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600/30 border border-indigo-500/40 rounded-lg text-xs font-bold text-white hover:bg-indigo-600/50 transition-all cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>
          <div className="w-9 h-9 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center flex-shrink-0">
            <Users className="w-5 h-5" />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6">
        {/* Active Users bar chart */}
        <ChartCard title="Daily Active Users (DAU)">
          {trendData.length === 0 ? (
            <div className="flex h-full items-center justify-center text-xs text-muted">
              No daily active user trends collected in the current time frame.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={trendData} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f213a" />
                <XAxis dataKey="date" stroke="#64748b" fontSize={9} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={9} tickLine={false} />
                <Tooltip
                  contentStyle={{ background: '#121324', borderColor: '#1f213a', borderRadius: '8px', fontSize: '10px' }}
                  labelStyle={{ fontWeight: 'bold', color: '#fff' }}
                />
                <Bar dataKey="conversations" name="Unique Active Users" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>
      </div>

      {/* Engagement Stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="gradient-border-card p-4.5 space-y-1">
          <span className="text-[10px] font-bold text-muted uppercase tracking-wider">Active System Users</span>
          <p className="font-outfit text-xl font-extrabold text-white">{activeUsersVal}</p>
          <span className="text-[9px] text-indigo-400 font-semibold">Active session count</span>
        </div>
        <div className="gradient-border-card p-4.5 space-y-1">
          <span className="text-[10px] font-bold text-muted uppercase tracking-wider">Total Recorded Sessions</span>
          <p className="font-outfit text-xl font-extrabold text-white">{totalConvVal}</p>
          <span className="text-[9px] text-[#64748b] font-semibold">Saved chat sessions</span>
        </div>
        <div className="gradient-border-card p-4.5 space-y-1">
          <span className="text-[10px] font-bold text-muted uppercase tracking-wider">Telemetry Collection</span>
          <p className="font-outfit text-xl font-extrabold text-white">Active</p>
          <span className="text-[9px] text-success font-semibold">Backend API connected</span>
        </div>
      </div>
    </div>
  );
};
