import React, { useEffect, useState } from 'react';
import { Shield } from 'lucide-react';
import { userService } from '../../services/api/userService';

interface RoleRow {
  name: string;
  usersCount: number;
  permissions: string[];
}

export const Roles: React.FC = () => {
  const [roles, setRoles] = useState<RoleRow[]>([]);

  useEffect(() => {
    userService.getRolesList().then((data) => setRoles(data));
  }, []);

  return (
    <div className="space-y-6">
      <div className="gradient-border-card p-5 flex items-center justify-between">
        <div className="space-y-1">
          <h2 className="text-sm font-extrabold text-white tracking-wider uppercase">Roles & Permissions</h2>
          <p className="text-xs text-muted">Manage granular role-based access control (RBAC) scopes and security profiles.</p>
        </div>
        <div className="w-9 h-9 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center flex-shrink-0">
          <Shield className="w-5 h-5" />
        </div>
      </div>

      <div className="gradient-border-card p-5">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-[#1f213a] text-muted font-bold text-[10px] uppercase tracking-wider">
                <th className="pb-2">Role Name</th>
                <th className="pb-2">Assigned Users</th>
                <th className="pb-2 text-right">Permitted Scopes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1f213a]/30 font-medium">
              {roles.map((role) => (
                <tr key={role.name} className="text-slate-300 hover:bg-white/[0.01] transition-all">
                  <td className="py-4 font-semibold text-white">{role.name}</td>
                  <td className="py-4 font-mono">{role.usersCount} Active</td>
                  <td className="py-4 text-right">
                    <div className="flex justify-end gap-1.5 flex-wrap max-w-lg ml-auto">
                      {role.permissions.map((perm, idx) => (
                        <span key={idx} className="inline-flex items-center px-2 py-0.5 bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 rounded text-[9px] font-bold uppercase tracking-wide">
                          {perm}
                        </span>
                      ))}
                    </div>
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
