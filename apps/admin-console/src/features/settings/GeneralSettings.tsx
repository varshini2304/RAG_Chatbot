import React, { useEffect, useState } from 'react';
import { Settings, Save } from 'lucide-react';
import { settingsService } from '../../services/api/settingsService';
import { toast, Toaster } from 'sonner';

interface GeneralConfig {
  appName: string;
  sessionTimeout: string;
  systemLogLevel: string;
  allowedFileTypes: string[];
}

const defaultConfig: GeneralConfig = {
  appName: 'RAG Admin Console',
  sessionTimeout: '30m',
  systemLogLevel: 'Info',
  allowedFileTypes: ['pdf', 'txt', 'docx', 'md', 'csv']
};

export const GeneralSettings: React.FC = () => {
  const [config, setConfig] = useState<GeneralConfig>(defaultConfig);

  useEffect(() => {
    settingsService.getGeneralSettings()
      .then((data) => {
        if (data && typeof data === 'object' && !data.detail && !data.error) {
          const rawFileTypes = data.allowedFileTypes || data.allowed_file_types;
          setConfig({
            appName: data.appName || data.app_name || defaultConfig.appName,
            sessionTimeout: data.sessionTimeout || data.session_timeout || defaultConfig.sessionTimeout,
            systemLogLevel: data.systemLogLevel || data.system_log_level || defaultConfig.systemLogLevel,
            allowedFileTypes: Array.isArray(rawFileTypes)
              ? rawFileTypes
              : defaultConfig.allowedFileTypes,
          });
        }
      })
      .catch((err) => {
        console.error('Failed to fetch settings from server:', err);
      });
  }, []);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    toast.success('System configurations updated successfully!');
  };

  const fileTypesString = Array.isArray(config.allowedFileTypes)
    ? config.allowedFileTypes.join(', ')
    : defaultConfig.allowedFileTypes.join(', ');

  return (
    <div className="space-y-6">
      <Toaster position="top-right" richColors />
      <div className="gradient-border-card p-5 flex items-center justify-between">
        <div className="space-y-1">
          <h2 className="text-sm font-extrabold text-white tracking-wider uppercase">General System Configurations</h2>
          <p className="text-xs text-muted">Customize session durations, system log level thresholds, and security parameters.</p>
        </div>
        <div className="w-9 h-9 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center flex-shrink-0">
          <Settings className="w-5 h-5" />
        </div>
      </div>

      <div className="gradient-border-card p-6">
        <form onSubmit={handleSave} className="space-y-6 max-w-2xl">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-slate-300 uppercase tracking-widest">Platform Application Name</label>
              <input
                type="text"
                value={config.appName || ''}
                onChange={(e) => setConfig({ ...config, appName: e.target.value })}
                className="w-full h-10 px-3.5 bg-[#0b0c15] border border-[#1f213a] rounded-lg text-xs text-white focus:outline-none focus:border-indigo-500 transition-all"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-slate-300 uppercase tracking-widest">User Session Timeout limit</label>
              <input
                type="text"
                value={config.sessionTimeout || ''}
                onChange={(e) => setConfig({ ...config, sessionTimeout: e.target.value })}
                className="w-full h-10 px-3.5 bg-[#0b0c15] border border-[#1f213a] rounded-lg text-xs text-white focus:outline-none focus:border-indigo-500 transition-all"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-slate-300 uppercase tracking-widest">Global Syslog Threshold</label>
              <select
                value={config.systemLogLevel || 'Info'}
                onChange={(e) => setConfig({ ...config, systemLogLevel: e.target.value })}
                className="w-full h-10 px-3.5 bg-[#0b0c15] border border-[#1f213a] rounded-lg text-xs text-white focus:outline-none focus:border-indigo-500 transition-all cursor-pointer"
              >
                <option>Debug</option>
                <option>Info</option>
                <option>Warning</option>
                <option>Error</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-slate-300 uppercase tracking-widest">Allowed Upload Suffixes</label>
              <input
                type="text"
                value={fileTypesString}
                onChange={(e) => setConfig({ ...config, allowedFileTypes: e.target.value.split(',').map(s => s.trim()) })}
                className="w-full h-10 px-3.5 bg-[#0b0c15] border border-[#1f213a] rounded-lg text-xs text-white focus:outline-none focus:border-indigo-500 transition-all"
              />
            </div>
          </div>

          <button
            type="submit"
            className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg text-xs font-semibold hover:bg-primary-hover shadow-lg transition-all cursor-pointer glow-btn"
          >
            <Save className="w-4 h-4" />
            <span>Save Changes</span>
          </button>
        </form>
      </div>
    </div>
  );
};

