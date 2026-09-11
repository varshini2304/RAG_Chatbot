import React, { useEffect } from 'react';
import { Cpu, Power } from 'lucide-react';
import { StatusBadge } from '../../shared/components/StatusBadge';
import { useProviderStore } from '../../store/providerStore';
import { toast, Toaster } from 'sonner';

export const Providers: React.FC = () => {
  const { providers, fetchProviders, toggleCircuitBreaker } = useProviderStore();

  useEffect(() => {
    fetchProviders();
  }, [fetchProviders]);

  const handleToggleCB = (name: string, state: string) => {
    toggleCircuitBreaker(name);
    const action = state === 'CLOSED' ? 'opened' : 'closed';
    toast.info(`Circuit breaker for ${name} has been manualy ${action}!`);
  };

  return (
    <div className="space-y-6">
      <Toaster position="top-right" richColors />
      <div className="gradient-border-card p-5 flex items-center justify-between">
        <div className="space-y-1">
          <h2 className="text-sm font-extrabold text-white tracking-wider uppercase">Model & LLM Providers</h2>
          <p className="text-xs text-muted">Monitor latency averages, circuit states, and toggle manual overrides for active backends.</p>
        </div>
        <div className="w-9 h-9 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center flex-shrink-0">
          <Cpu className="w-5 h-5" />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {providers.map((p) => {
          const isClosed = (p.circuitBreakerState || 'CLOSED') === 'CLOSED';
          const btnText = isClosed ? 'Trip Breaker' : 'Reset Breaker';
          const btnClass = isClosed ? 'bg-red-500/10 border-red-500/25 text-red-400 hover:bg-red-500/20' : 'bg-success/10 border-success/25 text-[#4ade80] hover:bg-success/20';
          const reqCount = (typeof p.requests === 'number' ? p.requests : 0).toLocaleString();
          const failCount = typeof p.failures === 'number' ? p.failures : 0;

          return (
            <div key={p.name} className="gradient-border-card p-5 flex flex-col justify-between h-[300px]">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex flex-col">
                    <span className="font-outfit text-sm font-extrabold text-white leading-tight">{p.name}</span>
                    <span className="text-[10px] text-muted mt-0.5 font-mono">{p.model}</span>
                  </div>
                  <StatusBadge status={p.status || 'Online'} />
                </div>

                <div className="space-y-2 text-xs font-medium text-slate-300">
                  <div className="flex justify-between border-b border-[#1f213a]/50 pb-1.5">
                    <span className="text-slate-400">Response Latency:</span>
                    <span className="text-white font-semibold">{p.latency || '0ms'}</span>
                  </div>
                  <div className="flex justify-between border-b border-[#1f213a]/50 pb-1.5">
                    <span className="text-slate-400">Total Requests:</span>
                    <span className="text-white font-mono">{reqCount}</span>
                  </div>
                  <div className="flex justify-between border-b border-[#1f213a]/50 pb-1.5">
                    <span className="text-slate-400">Failure Count:</span>
                    <span className="text-danger font-mono font-bold">{failCount}</span>
                  </div>
                  <div className="flex justify-between border-b border-[#1f213a]/50 pb-1.5">
                    <span className="text-slate-400">Success Rate:</span>
                    <span className="text-[#4ade80] font-semibold">{p.successRate || '100%'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Circuit Breaker:</span>
                    <span className={`font-bold ${isClosed ? 'text-success' : 'text-danger'}`}>{p.circuitBreakerState || 'CLOSED'}</span>
                  </div>
                </div>
              </div>

              <button
                onClick={() => handleToggleCB(p.name, p.circuitBreakerState || 'CLOSED')}
                className={`flex items-center justify-center gap-2 w-full py-2 border rounded-lg text-xs font-semibold cursor-pointer transition-all ${btnClass}`}
              >
                <Power className="w-3.5 h-3.5" />
                <span>{btnText}</span>
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
};
