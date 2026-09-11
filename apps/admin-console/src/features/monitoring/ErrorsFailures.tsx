import React, { useEffect, useState, useCallback } from 'react';
import { RefreshCw, XCircle } from 'lucide-react';
import { apiClient } from '../../services/axios';

interface ErrorRow {
  id?: string;
  time: string;
  timestamp?: string;
  level?: string;
  module?: string;
  type: string;
  provider: string;
  detail?: string;
  message?: string;
  status?: string;
}

export const ErrorsFailures: React.FC = () => {
  const [errorsList, setErrorsList] = useState<ErrorRow[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fetchErrors = useCallback(async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const response = await apiClient.get('/monitoring/errors');
      if (response.data && response.data.success && Array.isArray(response.data.data)) {
        setErrorsList(response.data.data);
      } else if (Array.isArray(response.data)) {
        setErrorsList(response.data);
      } else {
        setErrorsList([]);
      }
    } catch (err: unknown) {
      const msg = err && typeof err === 'object' && 'message' in err ? String((err as { message?: string }).message) : 'Failed to connect to error monitoring API';
      setErrorMsg(msg);
      setErrorsList([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      void fetchErrors();
    }, 0);
    return () => clearTimeout(timer);
  }, [fetchErrors]);

  const getLevelClasses = (level?: string) => {
    const normalized = (level || '').toUpperCase();
    if (normalized === 'ERROR') return 'bg-[#EF4444]/15 text-[#EF4444] border border-[#EF4444]/30';
    if (normalized === 'WARNING') return 'bg-[#F59E0B]/15 text-[#F59E0B] border border-[#F59E0B]/30';
    return 'bg-[#94A3B8]/15 text-[#94A3B8] border border-[#94A3B8]/30';
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between rounded-[18px] border border-white/[0.06] bg-[#161B2E] p-5">
        <div className="space-y-1">
          <h2 className="text-sm font-extrabold uppercase tracking-wider text-[#F8FAFC]">Chatbot Errors & Failover Logs</h2>
          <p className="text-xs text-[#94A3B8]">Inspect real warning, error, and provider failover logs from backend chatbot services.</p>
        </div>
        <button
          onClick={fetchErrors}
          disabled={isLoading}
          className="flex cursor-pointer items-center gap-1.5 rounded-[12px] border border-[#6D5DF6]/40 bg-[#6D5DF6]/20 px-3.5 py-1.5 text-xs font-bold text-white transition-all hover:bg-[#6D5DF6]/30"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {errorMsg && (
        <div className="rounded-[14px] border border-[#EF4444]/30 bg-[#EF4444]/15 p-3.5 text-xs text-[#EF4444]">
          {errorMsg}
        </div>
      )}

      <div className="enterprise-card rounded-[18px] border border-white/[0.06] bg-[#161B2E] p-5">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="border-b border-white/[0.06] text-[11px] font-bold uppercase tracking-wider text-[#94A3B8]">
                <th className="py-2.5 font-bold">Timestamp</th>
                <th className="py-2.5 font-bold">Level</th>
                <th className="py-2.5 font-bold">Module</th>
                <th className="py-2.5 font-bold">Message</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04] text-xs">
              {errorsList.length === 0 && !isLoading ? (
                <tr>
                  <td colSpan={4} className="rounded-xl border border-white/[0.04] bg-[#0B1020]/50 p-4 py-10 text-center text-xs font-semibold text-[#22C55E]">
                    No chatbot warning, error, or failover logs recorded.
                  </td>
                </tr>
              ) : (
                errorsList.map((err, idx) => (
                  <tr key={err.id || idx} className="transition-colors hover:bg-white/[0.02]">
                    <td className="whitespace-nowrap py-3">
                      <div className="flex items-center gap-1.5">
                        <XCircle className={`h-4 w-4 flex-shrink-0 ${(err.level || '').toUpperCase() === 'WARNING' ? 'text-[#F59E0B]' : 'text-[#EF4444]'}`} />
                        <span className="font-semibold text-[#F8FAFC]">{err.timestamp || err.time}</span>
                      </div>
                    </td>
                    <td className="whitespace-nowrap py-3">
                      <span className={`rounded-md px-2.5 py-0.5 text-[11px] font-bold ${getLevelClasses(err.level)}`}>
                        {err.level || 'ERROR'}
                      </span>
                    </td>
                    <td className="whitespace-nowrap py-3 font-mono text-[11px] text-[#94A3B8]">{err.module || 'app.llm'}</td>
                    <td className="max-w-[560px] truncate py-3 font-mono text-[11px] leading-relaxed text-[#F8FAFC]" title={err.detail || err.message}>
                      {err.detail || err.message || '—'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
