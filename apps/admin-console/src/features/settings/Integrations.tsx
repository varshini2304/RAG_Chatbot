import React, { useEffect, useState } from 'react';
import { Radio } from 'lucide-react';
import { StatusBadge } from '../../shared/components/StatusBadge';
import { settingsService } from '../../services/api/settingsService';

interface IntegrationRow {
  name: string;
  status: string;
  lastSync: string;
}

export const Integrations: React.FC = () => {
  const [integrations, setIntegrations] = useState<IntegrationRow[]>([]);

  useEffect(() => {
    settingsService.getIntegrations().then((data) => setIntegrations(data));
  }, []);

  return (
    <div className="space-y-6">
      <div className="gradient-border-card p-5 flex items-center justify-between">
        <div className="space-y-1">
          <h2 className="text-sm font-extrabold text-white tracking-wider uppercase">Connected Integrations</h2>
          <p className="text-xs text-muted">Configure external sync pipelines linking company portals directly to the RAG database.</p>
        </div>
        <div className="w-9 h-9 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center flex-shrink-0">
          <Radio className="w-5 h-5" />
        </div>
      </div>

      <div className="gradient-border-card p-5">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-[#1f213a] text-muted font-bold text-[10px] uppercase tracking-wider">
                <th className="pb-2">Integration Link</th>
                <th className="pb-2">Last Synchronized</th>
                <th className="pb-2 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1f213a]/30 font-medium">
              {integrations.map((item, idx) => (
                <tr key={idx} className="text-slate-300 hover:bg-white/[0.01] transition-all">
                  <td className="py-3.5 font-semibold text-white">{item.name}</td>
                  <td className="py-3.5 text-slate-400">{item.lastSync}</td>
                  <td className="py-3.5 text-right">
                    <StatusBadge status={item.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
