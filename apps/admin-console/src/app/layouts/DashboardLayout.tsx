import React, { useState, useRef, useEffect } from 'react';
import { Link, useLocation, useNavigate, Outlet } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { useDashboardStore } from '../../store/dashboardStore';
import { useAnalyticsStore } from '../../store/analyticsStore';
import { toast, Toaster } from 'sonner';
import {
  LayoutDashboard,
  BarChart3,
  Activity,
  Users,
  FileText,
  AlertOctagon,
  HeartPulse,
  Bell,
  Cpu,
  LogOut,
  Filter,
  Download,
  ChevronDown,
  CheckCircle2,
  X,
  SlidersHorizontal
} from 'lucide-react';

interface SidebarItem {
  name: string;
  path: string;
  icon: React.ComponentType<{ className?: string }>;
}

interface SidebarGroup {
  title: string;
  items: SidebarItem[];
}

export const DashboardLayout: React.FC = () => {
  const { user, logout, fetchProfile } = useAuthStore();
  const { fetchDashboardData } = useDashboardStore();
  const { fetchAnalyticsData } = useAnalyticsStore();
  const location = useLocation();
  const navigate = useNavigate();

  // Popover state handlers
  const [showFilterModal, setShowFilterModal] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [selectedRange, setSelectedRange] = useState('7d');
  const [selectedProviderFilter, setSelectedProviderFilter] = useState('all');

  const filterRef = useRef<HTMLDivElement>(null);
  const notifRef = useRef<HTMLDivElement>(null);
  const profileRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchProfile();
    const handleClickOutside = (e: MouseEvent) => {
      if (filterRef.current && !filterRef.current.contains(e.target as Node)) {
        setShowFilterModal(false);
      }
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setShowNotifications(false);
      }
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setShowProfileMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [fetchProfile]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const [isExporting, setIsExporting] = useState(false);

  const handleExportReport = async () => {
    if (isExporting) return;
    setIsExporting(true);
    const toastId = toast.loading('Generating enterprise report…');
    try {
      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
      const res = await fetch(`${apiBase}/export/report`, { method: 'GET' });
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const blob = await res.blob();
      const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
      const filename = `RAG_Admin_Report_${ts}.xlsx`;
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success('Enterprise Excel report downloaded!', { id: toastId });
    } catch (err) {
      console.error('Report export failed:', err);
      toast.error('Failed to generate enterprise report.', { id: toastId });
    } finally {
      setIsExporting(false);
    }
  };

  const applyFilters = () => {
    fetchDashboardData();
    fetchAnalyticsData();
    setShowFilterModal(false);
    toast.success(`Filter applied: ${selectedProviderFilter.toUpperCase()} (${selectedRange})`);
  };

  const navGroups: SidebarGroup[] = [
    {
      title: 'ANALYTICS',
      items: [
        { name: 'Usage Analytics', path: '/analytics/usage', icon: BarChart3 },
        { name: 'Performance', path: '/analytics/performance', icon: Activity },
      ],
    },
    {
      title: 'MONITORING',
      items: [
        { name: 'Logs', path: '/monitoring/logs', icon: FileText },
        { name: 'Errors & Failures', path: '/monitoring/errors', icon: AlertOctagon },
        { name: 'System Health', path: '/monitoring/health', icon: HeartPulse },
      ],
    },
    {
      title: 'MANAGEMENT',
      items: [
        { name: 'Providers', path: '/settings/providers', icon: Cpu },
        { name: 'Users', path: '/management/users', icon: Users },
      ],
    },
  ];

  return (
    <div className="flex h-screen w-full overflow-hidden bg-[#0B1020]">
      <Toaster position="top-right" richColors />

      {/* Fixed Sidebar (~280px) */}
      <aside className="flex flex-col w-[280px] border-r border-white/[0.06] bg-[#111827] flex-shrink-0 z-30">
        {/* Premium Logo Header */}
        <div className="flex items-center gap-3.5 px-6 py-6 border-b border-white/[0.06]">
          <div className="flex items-center justify-center w-10 h-10 rounded-2xl bg-gradient-to-br from-[#6D5DF6] to-indigo-700 shadow-lg shadow-[#6D5DF6]/30 flex-shrink-0">
            <svg viewBox="0 0 24 24" className="w-6 h-6 text-white" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <path d="M12 6v6l4 2"></path>
            </svg>
          </div>
          <div className="flex flex-col min-w-0">
            <span className="font-outfit text-base font-extrabold text-[#F8FAFC] tracking-wide leading-tight truncate">RAG Admin Console</span>
            <span className="text-[11px] text-[#94A3B8] font-medium tracking-wider truncate">Internal Document RAG</span>
          </div>
        </div>

        {/* Scrollable Navigation Items */}
        <div className="flex-1 min-h-0 px-4 py-5 overflow-y-auto space-y-6">
          <div>
            <p className="px-3 text-[11px] font-extrabold text-[#94A3B8] uppercase tracking-widest mb-2">MAIN</p>
            <Link
              to="/dashboard"
              className={`flex items-center gap-3.5 px-4 py-3 rounded-2xl text-sm font-bold tracking-wide transition-all duration-200 ${
                location.pathname === '/dashboard'
                  ? 'bg-[#6D5DF6] text-white shadow-lg shadow-[#6D5DF6]/30'
                  : 'text-[#94A3B8] hover:bg-white/[0.04] hover:text-[#F8FAFC]'
              }`}
            >
              <LayoutDashboard className="w-4.5 h-4.5" />
              <span>Overview</span>
            </Link>
          </div>

          {/* Nav Groups */}
          {navGroups.map((group) => (
            <div key={group.title} className="space-y-2">
              <p className="px-3 text-[11px] font-extrabold text-[#94A3B8] uppercase tracking-widest">{group.title}</p>
              <nav className="space-y-1">
                {group.items.map((item) => {
                  const isActive = location.pathname === item.path;
                  const ItemIcon = item.icon || LayoutDashboard;
                  return (
                    <Link
                      key={item.name}
                      to={item.path}
                      className={`flex items-center gap-3.5 px-4 py-2.5 rounded-2xl text-xs font-semibold transition-all duration-200 ${
                        isActive
                          ? 'bg-white/[0.08] text-[#F8FAFC] font-bold border border-white/[0.08]'
                          : 'text-[#94A3B8] hover:bg-white/[0.03] hover:text-[#F8FAFC]'
                      }`}
                    >
                      <ItemIcon className="w-4 h-4 flex-shrink-0" />
                      <span>{item.name}</span>
                    </Link>
                  );
                })}
              </nav>
            </div>
          ))}
        </div>

        {/* Bottom User profile & status cards */}
        <div className="p-4 border-t border-white/[0.06] space-y-3 bg-[#0D1322]">
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center gap-3 min-w-0">
              <div className="flex items-center justify-center w-9 h-9 rounded-full bg-gradient-to-br from-teal-500 to-emerald-600 text-white text-xs font-black shadow-md flex-shrink-0">
                {user?.avatarLetter || 'V'}
              </div>
              <div className="flex flex-col min-w-0">
                <span className="text-xs font-bold text-[#F8FAFC] truncate leading-tight">{user?.username || 'admin'}</span>
                <span className="text-[11px] text-[#94A3B8] truncate">{user?.role || 'Administrator'}</span>
              </div>
            </div>
            <button onClick={handleLogout} title="Logout" className="p-2 text-[#94A3B8] hover:text-white transition-colors cursor-pointer rounded-xl hover:bg-white/[0.05]">
              <LogOut className="w-4 h-4" />
            </button>
          </div>

          <div className="flex items-center gap-2.5 px-3.5 py-2.5 bg-[#0a1829] border border-[#1e3a5f] rounded-2xl text-xs font-bold text-[#38bdf8]">
            <span className="w-2.5 h-2.5 rounded-full bg-[#22C55E] animate-pulse"></span>
            <span>All Systems Operational</span>
          </div>
        </div>
      </aside>

      {/* Main Content Pane */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        {/* Top Header Toolbar */}
        <header className="flex items-center justify-between px-8 py-6 border-b border-white/[0.06] bg-[#0B1020] z-20">
          <div className="flex flex-col">
            <h1 className="font-outfit text-[40px] font-extrabold text-[#F8FAFC] leading-none tracking-tight">
              {(() => {
                const p = location.pathname;
                if (p.includes('/analytics/usage')) return 'Usage Analytics';
                if (p.includes('/analytics/performance')) return 'Performance';
                if (p.includes('/analytics/users')) return 'User Analytics';
                if (p.includes('/monitoring/logs')) return 'Logs';
                if (p.includes('/monitoring/errors')) return 'Errors & Failures';
                if (p.includes('/monitoring/health')) return 'System Health';
                if (p.includes('/settings/providers')) return 'Providers';
                if (p.includes('/settings/general')) return 'Settings';
                if (p.includes('/management/users')) return 'Users';
                return 'Overview';
              })()}
            </h1>
          </div>

          {/* Top Right Action & Profile Toolbar */}
          <div className="flex items-center gap-3">

            {/* Filter Button & Modal */}
            <div className="relative" ref={filterRef}>
              <button
                onClick={() => setShowFilterModal(!showFilterModal)}
                className="flex items-center gap-2 h-11 px-4 bg-[#161B2E] border border-white/10 rounded-[14px] text-sm font-bold text-[#F8FAFC] hover:bg-[#1f2642] hover:border-white/20 transition-all cursor-pointer shadow-sm"
              >
                <Filter className="w-4 h-4 text-[#6D5DF6]" />
                <span>Filter</span>
              </button>

              {showFilterModal && (
                <div className="absolute right-0 mt-2 w-72 bg-[#161B2E] border border-white/10 rounded-[18px] shadow-2xl p-4 z-50 space-y-4">
                  <div className="flex items-center justify-between border-b border-white/[0.06] pb-2">
                    <div className="flex items-center gap-2">
                      <SlidersHorizontal className="w-4 h-4 text-[#6D5DF6]" />
                      <span className="text-xs font-bold text-[#F8FAFC] uppercase tracking-wider">Filter Telemetry</span>
                    </div>
                    <button onClick={() => setShowFilterModal(false)} className="text-[#94A3B8] hover:text-white">
                      <X className="w-4 h-4" />
                    </button>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-[11px] font-bold text-[#94A3B8] uppercase tracking-wider">Time Range</label>
                    <select
                      value={selectedRange}
                      onChange={(e) => setSelectedRange(e.target.value)}
                      className="w-full h-9 px-3 bg-[#0B1020] border border-white/[0.08] rounded-[10px] text-xs text-[#F8FAFC] outline-none"
                    >
                      <option value="1d">Last 24 Hours</option>
                      <option value="7d">Last 7 Days</option>
                      <option value="30d">Last 30 Days</option>
                    </select>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-[11px] font-bold text-[#94A3B8] uppercase tracking-wider">Provider</label>
                    <select
                      value={selectedProviderFilter}
                      onChange={(e) => setSelectedProviderFilter(e.target.value)}
                      className="w-full h-9 px-3 bg-[#0B1020] border border-white/[0.08] rounded-[10px] text-xs text-[#F8FAFC] outline-none"
                    >
                      <option value="all">All Providers</option>
                      <option value="groq">Groq Cloud</option>
                      <option value="gemini">Google Gemini</option>
                      <option value="ollama">Ollama Server</option>
                    </select>
                  </div>

                  <button
                    onClick={applyFilters}
                    className="w-full h-9 bg-[#6D5DF6] hover:bg-[#5b4be0] text-white text-xs font-bold rounded-[10px] shadow-md transition-all cursor-pointer"
                  >
                    Apply Filter
                  </button>
                </div>
              )}
            </div>

            {/* Export Report Primary Action Button */}
            <button
              onClick={() => void handleExportReport()}
              disabled={isExporting}
              title="Download Enterprise Excel Report (.xlsx)"
              className={`flex items-center gap-2.5 h-11 px-5 text-white border rounded-[14px] text-sm font-bold shadow-lg transition-all cursor-pointer ${
                isExporting
                  ? 'bg-[#6D5DF6]/50 border-[#6D5DF6]/30 cursor-wait opacity-70'
                  : 'bg-[#6D5DF6] hover:bg-[#5b4be0] border-[#6D5DF6]/50 shadow-[#6D5DF6]/25'
              }`}
            >
              <Download className={`w-4 h-4 text-white ${isExporting ? 'animate-pulse' : ''}`} />
              <span>{isExporting ? 'Generating…' : 'Export Report'}</span>
            </button>

            <div className="h-6 w-px bg-white/[0.08] mx-1" />

            {/* Notifications Bell & Popover */}
            <div className="relative" ref={notifRef}>
              <button
                onClick={() => setShowNotifications(!showNotifications)}
                className="relative flex items-center justify-center w-11 h-11 bg-[#161B2E] border border-white/10 rounded-[14px] text-[#F8FAFC] hover:bg-[#1f2642] hover:border-white/20 transition-all cursor-pointer shadow-sm"
              >
                <Bell className="w-5 h-5 text-[#F8FAFC]" />
                <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-[#22C55E]" />
              </button>

              {showNotifications && (
                <div className="absolute right-0 mt-2 w-80 bg-[#161B2E] border border-white/10 rounded-[18px] shadow-2xl p-4 z-50 space-y-3">
                  <div className="flex items-center justify-between border-b border-white/[0.06] pb-2.5">
                    <span className="text-xs font-bold text-[#F8FAFC] uppercase tracking-wider">System Alerts & Notices</span>
                    <button onClick={() => setShowNotifications(false)} className="text-[#94A3B8] hover:text-white">
                      <X className="w-4 h-4" />
                    </button>
                  </div>

                  <div className="space-y-2.5 max-h-60 overflow-y-auto">
                    <div className="flex items-start gap-2.5 p-2 bg-[#0B1020] border border-white/[0.06] rounded-xl text-xs">
                      <CheckCircle2 className="w-4 h-4 text-[#22C55E] flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="font-bold text-[#F8FAFC]">ChromaDB Vector Store Healthy</p>
                        <p className="text-[10px] text-[#94A3B8] mt-0.5">Embeddings & chunk collections connected.</p>
                      </div>
                    </div>

                    <div className="flex items-start gap-2.5 p-2 bg-[#0B1020] border border-white/[0.06] rounded-xl text-xs">
                      <CheckCircle2 className="w-4 h-4 text-[#38BDF8] flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="font-bold text-[#F8FAFC]">Primary Model Provider Active</p>
                        <p className="text-[10px] text-[#94A3B8] mt-0.5">Groq Cloud operating normally.</p>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Profile Dropdown Menu */}
            <div className="relative" ref={profileRef}>
              <div
                onClick={() => setShowProfileMenu(!showProfileMenu)}
                className="flex items-center gap-3 px-3 py-1.5 bg-[#161B2E] border border-white/10 rounded-[14px] hover:bg-[#1f2642] hover:border-white/20 transition-all cursor-pointer shadow-sm"
              >
                <div className="flex items-center justify-center w-8 h-8 rounded-full bg-gradient-to-br from-teal-500 to-emerald-600 text-white text-xs font-black shadow-md">
                  {user?.avatarLetter || 'A'}
                </div>
                <div className="hidden lg:flex flex-col text-left">
                  <span className="text-xs font-bold text-[#F8FAFC] leading-tight">{user?.username || 'admin'}</span>
                  <span className="text-[11px] text-[#94A3B8]">{user?.role || 'Administrator'}</span>
                </div>
                <ChevronDown className="w-4 h-4 text-[#94A3B8]" />
              </div>

              {showProfileMenu && (
                <div className="absolute right-0 mt-2 w-48 bg-[#161B2E] border border-white/10 rounded-[18px] shadow-2xl py-2 z-50 space-y-1">
                  <button
                    onClick={handleLogout}
                    className="flex items-center gap-2.5 w-full text-left px-4 py-2 text-xs font-semibold text-[#EF4444] hover:bg-white/[0.05] cursor-pointer"
                  >
                    <LogOut className="w-4 h-4 text-[#EF4444]" />
                    <span>Logout</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Content Outlet with 24px Page Padding & Gaps */}
        <main className="flex-1 overflow-y-auto p-6 space-y-6 bg-[#0B1020]">
          <Outlet />

          <footer className="flex items-center justify-center gap-2 pt-6 pb-2 text-[13px] text-[#94A3B8] tracking-wide font-medium">
            <svg viewBox="0 0 24 24" className="w-4 h-4 text-[#94A3B8]" fill="none" stroke="currentColor" strokeWidth="2.5">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="16" x2="12" y2="12"></line>
              <line x1="12" y1="8" x2="12.01" y2="8"></line>
            </svg>
            <span>Dashboard data is aggregated and anonymized. No user queries or document content are stored or displayed.</span>
          </footer>
        </main>
      </div>
    </div>
  );
};
