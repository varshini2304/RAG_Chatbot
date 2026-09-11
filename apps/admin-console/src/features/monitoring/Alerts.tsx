import React, { useEffect, useState, useCallback } from 'react';
import { RefreshCw } from 'lucide-react';
import { StatusBadge } from '../../shared/components/StatusBadge';
import { apiClient } from '../../services/axios';

interface AlertItem {
  id?: string;
  rule?: string;
  title?: string;
  triggerCondition?: string;
  message?: string;
  severity: string;
  status?: string;
  acknowledged?: boolean;
}

export const Alerts: React.FC = () => {
  const [alertsList, setAlertsList] = useState<AlertItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchAlerts = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.get('/monitoring/alerts');
      if (response.data && response.data.success && Array.isArray(response.data.data)) {
        setAlertsList(response.data.data);
      } else if (Array.isArray(response.data)) {
        setAlertsList(response.data);
      } else {
        setAlertsList([]);
      }
    } catch {
      setAlertsList([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      void fetchAlerts();
    }, 0);
    return () => clearTimeout(timer);
  }, [fetchAlerts]);

  return (
    <div className="space-y-6">
      <div className="gradient-border-card p-5 flex items-center justify-between">
        <div className="space-y-1">
          <h2 className="text-sm font-extrabold text-white tracking-wider uppercase">System Alerts Configuration</h2>
          <p className="text-xs text-muted">Manage real-time alert trigger parameters and webhook dispatch rules live from backend services.</p>
        </div>
        <button
          onClick={fetchAlerts}
          disabled={isLoading}
          className="flex items-center gap-1.5 px-3 py-2 bg-indigo-600/30 border border-indigo-500/40 rounded-lg text-xs font-bold text-white hover:bg-indigo-600/50 transition-all cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      <div className="gradient-border-card p-5">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-[#1f213a] text-muted font-bold text-[10px] uppercase tracking-wider">
                <th className="pb-2">Rule Name</th>
                <th className="pb-2">Trigger Condition / Message</th>
                <th className="pb-2">Severity</th>
                <th className="pb-2 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1f213a]/30 font-medium">
              {alertsList.length === 0 && !isLoading ? (
                <tr>
                  <td colSpan={4} className="py-8 text-center text-xs text-muted">
                    No system alerts currently triggered.
                  </td>
                </tr>
              ) : (
                alertsList.map((rule, idx) => {
                  const isCrit = rule.severity.toLowerCase() === 'critical';
                  const sevColor = isCrit ? 'text-danger bg-danger/10 border-danger/25' : 'text-warning bg-warning/10 border-warning/25';
                  
                  return (
                    <tr key={rule.id || idx} className="text-slate-300 hover:bg-white/[0.01] transition-all">
                      <td className="py-3.5 font-semibold text-white">{rule.rule || rule.title}</td>
                      <td className="py-3.5 text-slate-400">{rule.triggerCondition || rule.message}</td>
                      <td className="py-3.5">
                        <span className={`inline-flex px-2 py-0.5 rounded border text-[9px] font-bold uppercase tracking-wider ${sevColor}`}>
                          {rule.severity}
                        </span>
                      </td>
                      <td className="py-3.5 text-right">
                        <StatusBadge status={rule.status || (rule.acknowledged ? 'Acknowledged' : 'Active')} />
                      </td>
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
