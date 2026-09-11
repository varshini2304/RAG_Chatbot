import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { DashboardLayout } from '../layouts/DashboardLayout';
import { AuthGuard } from '../guards/AuthGuard';
import { Login } from '../../features/authentication/Login';
import { Dashboard } from '../../features/dashboard/Dashboard';
import { UsageAnalytics } from '../../features/analytics/UsageAnalytics';
import { Performance } from '../../features/analytics/Performance';
import { SystemHealth } from '../../features/monitoring/SystemHealth';
import { Logs } from '../../features/monitoring/Logs';
import { ErrorsFailures } from '../../features/monitoring/ErrorsFailures';
import { Users } from '../../features/users/Users';
import { Roles } from '../../features/roles/Roles';
import { ApiKeys } from '../../features/api-keys/ApiKeys';
import { Providers } from '../../features/providers/Providers';
import { Integrations } from '../../features/settings/Integrations';
import { Profile } from '../../features/settings/Profile';
import { NotFound } from '../../shared/components/NotFound';

// Mock empty layout for workspace placeholders
const DocumentPlaceholder: React.FC<{ title: string; desc: string }> = ({ title, desc }) => (
  <div className="gradient-border-card p-10 flex flex-col items-center justify-center text-center space-y-4 min-h-[400px]">
    <div className="w-12 h-12 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center">
      <svg viewBox="0 0 24 24" className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="2.5">
        <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"></path>
        <polyline points="14 2 14 8 20 8"></polyline>
      </svg>
    </div>
    <h3 className="font-outfit text-sm font-extrabold text-white tracking-wide uppercase">{title}</h3>
    <p className="text-xs text-muted max-w-sm">{desc}</p>
  </div>
);

export const AppRouter: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        {/* Unauthenticated routes */}
        <Route path="/login" element={<Login />} />

        {/* Authenticated dashboard frame routes */}
        <Route
          path="/"
          element={
            <AuthGuard>
              <DashboardLayout />
            </AuthGuard>
          }
        >
          {/* Default redirect to Overview dashboard */}
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />

          {/* Analytics group */}
          <Route path="analytics/usage" element={<UsageAnalytics />} />
          <Route path="analytics/performance" element={<Performance />} />
          <Route path="analytics/users" element={<Navigate to="/analytics/usage" replace />} />

          {/* Monitoring group */}
          <Route path="monitoring/health" element={<SystemHealth />} />
          <Route path="monitoring/logs" element={<Logs />} />
          <Route path="monitoring/errors" element={<ErrorsFailures />} />

          {/* Management group */}
          <Route path="management/documents" element={<DocumentPlaceholder title="Document Ingestion Center" desc="Manage vector upload pipelines and verify chunk extractions." />} />
          <Route path="management/knowledge" element={<DocumentPlaceholder title="Knowledge Base Hub" desc="Review indexed text chunks, parent source mappings, and vector similarity properties." />} />
          <Route path="management/users" element={<Users />} />
          <Route path="management/roles" element={<Roles />} />
          <Route path="management/api-keys" element={<ApiKeys />} />

          {/* Settings group */}
          <Route path="settings/general" element={<Navigate to="/dashboard" replace />} />
          <Route path="settings/providers" element={<Providers />} />
          <Route path="settings/integrations" element={<Integrations />} />
          <Route path="settings/profile" element={<Profile />} />

          {/* Catch-all route inside dashboard layout */}
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};
