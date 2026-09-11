import React, { useState, useEffect, useCallback } from 'react';
import { FileText, Search, RefreshCw } from 'lucide-react';
import { apiClient } from '../../services/axios';

interface LogRow {
  id?: string;
  timestamp: string;
  level: string;
  module: string;
  message: string;
  details?: string | null;
}

export const Logs: React.FC = () => {
  const [search, setSearch] = useState('');
  const [selectedLevel, setSelectedLevel] = useState<string>('ALL');
  const [logs, setLogs] = useState<LogRow[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchLogs = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = {};
      if (search.trim()) params.search = search.trim();
      if (selectedLevel !== 'ALL') params.level = selectedLevel;

      const response = await apiClient.get('/monitoring/logs', { params });
      if (response.data && response.data.success && Array.isArray(response.data.data)) {
        setLogs(response.data.data);
      } else if (Array.isArray(response.data)) {
        setLogs(response.data);
      } else {
        setLogs([]);
      }
    } catch (err: unknown) {
      const msg = err && typeof err === 'object' && 'message' in err ? String((err as { message?: string }).message) : 'Failed to connect to log monitoring backend';
      setError(msg);
      setLogs([]);
    } finally {
      setIsLoading(false);
    }
  }, [search, selectedLevel]);

  useEffect(() => {
    const timer = setTimeout(() => {
      void fetchLogs();
    }, 0);
    return () => clearTimeout(timer);
  }, [fetchLogs]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchLogs();
  };

  return (
    <div className="space-y-6">
      <div className="gradient-border-card p-5 flex items-center justify-between">
        <div className="space-y-1">
          <h2 className="text-sm font-extrabold text-white tracking-wider uppercase">System Activity Logs</h2>
          <p className="text-xs text-muted">Inspect FastAPI request audits, RAG pipeline execution, and failover router logs live from the backend API.</p>
        </div>
        <div className="w-9 h-9 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center flex-shrink-0">
          <FileText className="w-5 h-5" />
        </div>
      </div>

      <div className="gradient-border-card p-5 space-y-4">
        {/* Controls row */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
          <form onSubmit={handleSearchSubmit} className="flex items-center gap-3 w-full sm:w-96 h-10 px-3 bg-[#0b0c15] border border-[#1f213a] rounded-lg">
            <Search className="w-4 h-4 text-slate-500 flex-shrink-0" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search log message or module..."
              className="w-full bg-transparent border-none text-xs text-white placeholder-slate-500 focus:outline-none"
            />
          </form>

          <div className="flex items-center gap-2">
            <select
              value={selectedLevel}
              onChange={(e) => setSelectedLevel(e.target.value)}
              className="bg-[#0b0c15] border border-[#1f213a] rounded-lg px-3 py-2 text-xs text-slate-300 font-semibold outline-none cursor-pointer"
            >
              <option value="ALL">All Levels</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARN / WARNING</option>
              <option value="ERROR">ERROR</option>
              <option value="DEBUG">DEBUG</option>
            </select>

            <button
              onClick={fetchLogs}
              disabled={isLoading}
              className="flex items-center gap-1.5 px-3 py-2 bg-indigo-600/30 border border-indigo-500/40 rounded-lg text-xs font-bold text-white hover:bg-indigo-600/50 transition-all cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {error && (
          <div className="p-3 bg-red-900/20 border border-red-500/30 rounded-lg text-xs text-red-300">
            {error}
          </div>
        )}

        {/* Logs Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-[#1f213a] text-muted font-bold text-[10px] uppercase tracking-wider">
                <th className="pb-2">Timestamp</th>
                <th className="pb-2">Level</th>
                <th className="pb-2">Module</th>
                <th className="pb-2">Message</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1f213a]/30 font-medium">
              {logs.length === 0 && !isLoading ? (
                <tr>
                  <td colSpan={4} className="py-8 text-center text-xs text-muted">
                    No runtime log entries match the selected filter.
                  </td>
                </tr>
              ) : (
                logs.map((log, idx) => {
                  const isError = log.level.toUpperCase() === 'ERROR';
                  const isWarning = log.level.toUpperCase().includes('WARN');
                  const levelColor = isError ? 'text-danger' : isWarning ? 'text-warning' : 'text-indigo-400';
                  
                  return (
                    <tr key={log.id || idx} className="text-slate-300 hover:bg-white/[0.01] transition-all">
                      <td className="py-2.5 font-mono text-[11px] whitespace-nowrap">{log.timestamp}</td>
                      <td className={`py-2.5 font-extrabold ${levelColor}`}>{log.level}</td>
                      <td className="py-2.5 font-semibold text-white truncate max-w-[160px]">{log.module}</td>
                      <td className="py-2.5 text-slate-300">{log.message}</td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
