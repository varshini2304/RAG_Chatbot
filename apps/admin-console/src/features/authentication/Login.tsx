import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { CircleAlert, Eye, EyeOff, ShieldCheck, Loader2 } from 'lucide-react';

export const Login: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const { isAuthenticated, login } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();

  const from =
    (location.state as { from?: { pathname?: string } })?.from?.pathname ||
    '/dashboard';

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim()) {
      setError('Username is required.');
      return;
    }
    if (!password) {
      setError('Password is required.');
      return;
    }

    setError(null);
    setLoading(true);

    try {
      const result = await login(username, password);
      if (result.success) {
        navigate(from, { replace: true });
      } else {
        setError(result.message);
      }
    } catch {
      setError('An unexpected error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex items-center justify-center min-h-screen bg-[#080B18] px-4 overflow-hidden">
      {/* Ambient background blobs */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-indigo-600/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-0 right-1/4 w-80 h-80 bg-violet-600/10 rounded-full blur-[100px] pointer-events-none" />

      <div className="w-full max-w-[420px] relative z-10">
        {/* Card */}
        <div className="bg-[#0F1629]/90 border border-white/[0.07] rounded-2xl shadow-2xl shadow-black/50 overflow-hidden">

          {/* Top accent bar */}
          <div className="h-[3px] w-full bg-gradient-to-r from-indigo-500 via-violet-500 to-indigo-500" />

          <div className="px-8 pt-8 pb-9">
            {/* Brand Header */}
            <div className="flex flex-col items-center mb-9">
              <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 shadow-lg shadow-indigo-500/30 mb-5">
                <ShieldCheck className="w-7 h-7 text-white" strokeWidth={2} />
              </div>
              <h1 className="font-outfit text-[22px] font-extrabold text-white tracking-tight leading-tight text-center">
                RAG Admin Console
              </h1>
              <p className="text-[12px] text-slate-400 mt-1.5 text-center leading-relaxed">
                Restricted access — authorised personnel only
              </p>
            </div>

            {/* Form */}
            <form onSubmit={(e) => void handleSubmit(e)} className="space-y-5" noValidate>

              {/* Error banner */}
              {error && (
                <div
                  role="alert"
                  className="flex items-start gap-2.5 p-3.5 rounded-xl border border-red-500/20 bg-red-500/8 text-red-400 text-[12px] font-medium"
                >
                  <CircleAlert className="w-4 h-4 flex-shrink-0 mt-px" />
                  <span>{error}</span>
                </div>
              )}

              {/* Username */}
              <div className="space-y-2">
                <label
                  htmlFor="login-username"
                  className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest"
                >
                  Username
                </label>
                <input
                  id="login-username"
                  type="text"
                  autoComplete="username"
                  autoFocus
                  value={username}
                  onChange={(e) => { setUsername(e.target.value); setError(null); }}
                  placeholder="Enter your username"
                  className="w-full h-11 px-4 bg-[#080B18] border border-white/[0.09] rounded-xl text-[13px] text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500/70 focus:ring-1 focus:ring-indigo-500/20 transition-all"
                />
              </div>

              {/* Password */}
              <div className="space-y-2">
                <label
                  htmlFor="login-password"
                  className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest"
                >
                  Password
                </label>
                <div className="relative">
                  <input
                    id="login-password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => { setPassword(e.target.value); setError(null); }}
                    placeholder="Enter your password"
                    className="w-full h-11 px-4 pr-11 bg-[#080B18] border border-white/[0.09] rounded-xl text-[13px] text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500/70 focus:ring-1 focus:ring-indigo-500/20 transition-all"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
                    tabIndex={-1}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Submit */}
              <button
                id="login-submit-btn"
                type="submit"
                disabled={loading}
                className="flex items-center justify-center gap-2.5 w-full h-11 mt-1 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 disabled:cursor-not-allowed text-white rounded-xl text-[13px] font-bold shadow-lg shadow-indigo-600/25 hover:shadow-indigo-500/35 transition-all cursor-pointer"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Signing in…</span>
                  </>
                ) : (
                  <span>Sign In</span>
                )}
              </button>
            </form>

            {/* Footer note */}
            <p className="mt-7 text-center text-[11px] text-slate-600 leading-relaxed">
              Account access is managed by your system administrator.
              <br />Contact admin to request access.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
