import React, { useEffect } from 'react';
import { ProgressBar } from '../../shared/components/ProgressBar';
import { HeartPulse, CheckCircle, AlertTriangle, Loader2 } from 'lucide-react';
import { useDashboardStore } from '../../store/dashboardStore';

export const SystemHealth: React.FC = () => {
  const { systemHealth, fetchDashboardData, isLoading } = useDashboardStore();

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  const cpu = systemHealth?.cpuUsage ?? systemHealth?.cpu_usage_pct ?? 0;
  const memory = systemHealth?.memoryUsage ?? systemHealth?.memory_usage_pct ?? 0;
  const disk = systemHealth?.diskUsage ?? systemHealth?.disk_usage_pct ?? 0;

  const apiStatus = (systemHealth?.apiStatus ?? systemHealth?.api_status ?? 'healthy').toLowerCase();
  const chromaStatus = (systemHealth?.chromaDb ?? systemHealth?.chroma_db ?? systemHealth?.vector_db_status ?? 'healthy').toLowerCase();
  const embeddingStatus = (systemHealth?.embeddingService ?? systemHealth?.embedding_service ?? systemHealth?.embedding_status ?? 'healthy').toLowerCase();
  const ollamaStatus = (systemHealth?.ollamaServer ?? systemHealth?.ollama_server ?? systemHealth?.ollama_server_status ?? 'running').toLowerCase();

  return (
    <div className="space-y-6">
      <div className="gradient-border-card p-5 flex items-center justify-between">
        <div className="space-y-1">
          <h2 className="text-sm font-extrabold text-white tracking-wider uppercase">System Resource & Health Status</h2>
          <p className="text-xs text-muted">Verify core microservices status, system load averages, and database indexes health.</p>
        </div>
        <div className="w-9 h-9 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center flex-shrink-0">
          <HeartPulse className="w-5 h-5" />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Core Services Check Card */}
        <div className="gradient-border-card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-outfit text-xs font-bold text-white tracking-wide uppercase">Core Platform Services</h3>
            {isLoading && <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />}
          </div>
          <div className="space-y-3.5">
            <div className="flex items-center justify-between border-b border-[#1f213a]/50 pb-2.5">
              <span className="text-xs font-semibold text-slate-300">FastAPI Gateway API</span>
              <div className={`flex items-center gap-1.5 text-xs font-extrabold ${apiStatus === 'healthy' || apiStatus === 'online' ? 'text-success' : 'text-rose-400'}`}>
                {apiStatus === 'healthy' || apiStatus === 'online' ? <CheckCircle className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
                <span className="uppercase">{apiStatus}</span>
              </div>
            </div>

            <div className="flex items-center justify-between border-b border-[#1f213a]/50 pb-2.5">
              <span className="text-xs font-semibold text-slate-300">ChromaDB Vector Store</span>
              <div className={`flex items-center gap-1.5 text-xs font-extrabold ${chromaStatus === 'healthy' || chromaStatus === 'online' ? 'text-success' : 'text-amber-400'}`}>
                {chromaStatus === 'healthy' || chromaStatus === 'online' ? <CheckCircle className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
                <span className="uppercase">{chromaStatus}</span>
              </div>
            </div>

            <div className="flex items-center justify-between border-b border-[#1f213a]/50 pb-2.5">
              <span className="text-xs font-semibold text-slate-300">BGE-M3 Embedding Engine</span>
              <div className={`flex items-center gap-1.5 text-xs font-extrabold ${embeddingStatus === 'healthy' || embeddingStatus === 'online' ? 'text-success' : 'text-amber-400'}`}>
                {embeddingStatus === 'healthy' || embeddingStatus === 'online' ? <CheckCircle className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
                <span className="uppercase">{embeddingStatus}</span>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-300">Ollama Local SLM Server</span>
              <div className={`flex items-center gap-1.5 text-xs font-extrabold ${ollamaStatus === 'running' || ollamaStatus === 'healthy' || ollamaStatus === 'available' ? 'text-success' : 'text-amber-400'}`}>
                {ollamaStatus === 'running' || ollamaStatus === 'healthy' || ollamaStatus === 'available' ? <CheckCircle className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
                <span className="uppercase">{ollamaStatus}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Server utilization progress indicators */}
        <div className="gradient-border-card p-5 space-y-5">
          <h3 className="font-outfit text-xs font-bold text-white tracking-wide uppercase">Server Hardware Load</h3>
          <div className="space-y-4.5">
            <ProgressBar label="CPU Core Load" value={cpu} color="bg-indigo-500" />
            <ProgressBar label="Memory Buffer Utilization" value={memory} color="bg-blue-500" />
            <ProgressBar label="SSD Disk Storage space used" value={disk} color="bg-amber-500" />
          </div>
        </div>
      </div>
    </div>
  );
};
