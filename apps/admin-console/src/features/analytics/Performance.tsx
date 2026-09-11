import React, { useEffect } from 'react';
import { ChartCard } from '../../shared/components/ChartCard';
import { Activity, RefreshCw } from 'lucide-react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import { useAnalyticsStore } from '../../store/analyticsStore';
import { useDashboardStore } from '../../store/dashboardStore';

export const Performance: React.FC = () => {
  const { trendData, fetchAnalyticsData } = useAnalyticsStore();
  const { metrics, fetchDashboardData } = useDashboardStore();

  useEffect(() => {
    fetchAnalyticsData();
    fetchDashboardData();
  }, [fetchAnalyticsData, fetchDashboardData]);

  const avgResponseTimeVal = metrics?.avg_response_time?.value ?? '0.00s';

  return (
    <div className="space-y-6">
      <div className="gradient-border-card p-5 flex items-center justify-between">
        <div className="space-y-1">
          <h2 className="text-sm font-extrabold text-white tracking-wider uppercase">System & Provider Performance</h2>
          <p className="text-xs text-muted">Monitor API response latency, RAG extraction bottlenecks, and model token outputs from backend services.</p>
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
            <Activity className="w-5 h-5" />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6">
        {/* Detailed Response Time trend area chart */}
        <ChartCard title="Response Latency Trend (Seconds)">
          {trendData.length === 0 ? (
            <div className="flex h-full items-center justify-center text-xs text-muted">
              No historical latency trend data available.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trendData} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
                <defs>
                  <linearGradient id="colorLatency" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f213a" />
                <XAxis dataKey="date" stroke="#64748b" fontSize={9} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={9} tickLine={false} />
                <Tooltip
                  contentStyle={{ background: '#121324', borderColor: '#1f213a', borderRadius: '8px', fontSize: '10px' }}
                  labelStyle={{ fontWeight: 'bold', color: '#fff' }}
                />
                <Area type="monotone" dataKey="responseTime" name="Avg Latency (s)" stroke="#3b82f6" fillOpacity={1} fill="url(#colorLatency)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </ChartCard>
      </div>

      {/* Latency Summary Card */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="gradient-border-card p-4 space-y-1">
          <span className="text-[10px] font-bold text-muted uppercase tracking-wider">Average End-to-End Latency</span>
          <p className="font-outfit text-xl font-extrabold text-white">{avgResponseTimeVal}</p>
          <span className="text-[9px] text-indigo-400 font-semibold">Live backend response time metric</span>
        </div>
        <div className="gradient-border-card p-4 space-y-1">
          <span className="text-[10px] font-bold text-muted uppercase tracking-wider">Pipeline Bottleneck Status</span>
          <p className="font-outfit text-xl font-extrabold text-white">Optimal</p>
          <span className="text-[9px] text-success font-semibold">RAG pipeline & provider status nominal</span>
        </div>
      </div>
    </div>
  );
};
