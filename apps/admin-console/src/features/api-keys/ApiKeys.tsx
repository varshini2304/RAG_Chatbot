import { Plus } from 'lucide-react';
import { StatusBadge } from '../../shared/components/StatusBadge';
import { userService } from '../../services/api/userService';
import React, { useEffect, useState } from 'react';

interface ApiKeyRow {
  id: number;
  name: string;
  keyPrefix: string;
  status: string;
  created: string;
}

export const ApiKeys: React.FC = () => {
  const [keys, setKeys] = useState<ApiKeyRow[]>([]);

  useEffect(() => {
    userService.getApiKeys().then((data) => setKeys(data));
  }, []);

  return (
    <div className="space-y-6">
      <div className="gradient-border-card p-5 flex items-center justify-between">
        <div className="space-y-1">
          <h2 className="text-sm font-extrabold text-white tracking-wider uppercase">API Integrations Keys</h2>
          <p className="text-xs text-muted">Generate tokens to connect third-party clients and microservices to the retrieval APIs.</p>
        </div>
        <button className="flex items-center gap-2 px-3 py-1.5 bg-primary text-white rounded-lg text-xs font-semibold hover:bg-primary-hover shadow-lg transition-all cursor-pointer glow-btn">
          <Plus className="w-3.5 h-3.5" />
          <span>Generate Key</span>
        </button>
      </div>

      <div className="gradient-border-card p-5">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-[#1f213a] text-muted font-bold text-[10px] uppercase tracking-wider">
                <th className="pb-2">Token Name</th>
                <th className="pb-2">API Key Prefix</th>
                <th className="pb-2">Date Created</th>
                <th className="pb-2 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1f213a]/30 font-medium">
              {keys.map((key) => (
                <tr key={key.id} className="text-slate-300 hover:bg-white/[0.01] transition-all">
                  <td className="py-3.5 font-semibold text-white">{key.name}</td>
                  <td className="py-3.5 font-mono text-slate-400">{key.keyPrefix}</td>
                  <td className="py-3.5">{key.created}</td>
                  <td className="py-3.5 text-right">
                    <StatusBadge status={key.status} />
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
