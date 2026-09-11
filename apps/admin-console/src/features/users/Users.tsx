import React, { useEffect, useState, useCallback } from 'react';
import { UserPlus, RefreshCw } from 'lucide-react';
import { StatusBadge } from '../../shared/components/StatusBadge';
import { userService } from '../../services/api/userService';

interface UserRow {
  id: number;
  name: string;
  email?: string | null;
  role: string;
  status: string;
}

export const Users: React.FC = () => {
  const [users, setUsers] = useState<UserRow[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchUsers = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await userService.getUsersList();
      if (Array.isArray(data)) {
        setUsers(data);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      void fetchUsers();
    }, 0);
    return () => clearTimeout(timer);
  }, [fetchUsers]);

  return (
    <div className="space-y-6">
      <div className="gradient-border-card p-5 flex items-center justify-between">
        <div className="space-y-1">
          <h2 className="text-sm font-extrabold text-white tracking-wider uppercase">User Management</h2>
          <p className="text-xs text-muted">Configure portal administrator roles, edit profile logins, and audit account access live from registered user storage.</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchUsers}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600/30 border border-indigo-500/40 rounded-lg text-xs font-bold text-white hover:bg-indigo-600/50 transition-all cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <button className="flex items-center gap-2 px-3 py-1.5 bg-primary text-white rounded-lg text-xs font-semibold hover:bg-primary-hover shadow-lg transition-all cursor-pointer glow-btn">
            <UserPlus className="w-3.5 h-3.5" />
            <span>Add User</span>
          </button>
        </div>
      </div>

      <div className="gradient-border-card p-5">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-[#1f213a] text-muted font-bold text-[10px] uppercase tracking-wider">
                <th className="pb-2">User ID</th>
                <th className="pb-2">Full Name</th>
                <th className="pb-2">Email Address</th>
                <th className="pb-2">Role Assigned</th>
                <th className="pb-2 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1f213a]/30 font-medium">
              {users.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-xs text-muted">
                    No registered user accounts found.
                  </td>
                </tr>
              ) : (
                users.map((usr) => (
                  <tr key={usr.id} className="text-slate-300 hover:bg-white/[0.01] transition-all">
                    <td className="py-3.5 font-mono">USR-0{usr.id}</td>
                    <td className="py-3.5 font-semibold text-white">{usr.name}</td>
                    <td className="py-3.5 text-slate-400">{usr.email || '—'}</td>
                    <td className="py-3.5">{usr.role}</td>
                    <td className="py-3.5 text-right">
                      <StatusBadge status={usr.status} />
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
