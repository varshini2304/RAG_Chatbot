import React from 'react';
import { useAuthStore } from '../../store/authStore';
import { User, Save } from 'lucide-react';
import { toast, Toaster } from 'sonner';

export const Profile: React.FC = () => {
  const { user } = useAuthStore();

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    toast.success('User profile updated successfully!');
  };

  return (
    <div className="space-y-6">
      <Toaster position="top-right" richColors />
      <div className="gradient-border-card p-5 flex items-center justify-between">
        <div className="space-y-1">
          <h2 className="text-sm font-extrabold text-white tracking-wider uppercase">User Profile Details</h2>
          <p className="text-xs text-muted">Update administrative login credentials, password hash, and display settings.</p>
        </div>
        <div className="w-9 h-9 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center flex-shrink-0">
          <User className="w-5 h-5" />
        </div>
      </div>

      <div className="gradient-border-card p-6 flex flex-col md:flex-row gap-8 items-start">
        {/* Avatar badge */}
        <div className="flex flex-col items-center gap-3">
          <div className="w-24 h-24 rounded-full bg-gradient-to-br from-purple-500 to-purple-700 text-white text-3xl font-extrabold flex items-center justify-center shadow-xl">
            {user?.avatarLetter || 'A'}
          </div>
          <span className="text-xs font-bold text-indigo-400 uppercase tracking-widest">{user?.role || 'Administrator'}</span>
        </div>

        {/* Details Form */}
        <form onSubmit={handleSave} className="flex-grow space-y-5 max-w-xl">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-slate-300 uppercase tracking-widest">Username</label>
              <input
                type="text"
                defaultValue={user?.username || 'admin'}
                className="w-full h-10 px-3.5 bg-[#0b0c15] border border-[#1f213a] rounded-lg text-xs text-white focus:outline-none focus:border-indigo-500 transition-all"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-slate-300 uppercase tracking-widest">Email Address</label>
              <input
                type="email"
                defaultValue={user?.email || ''}
                placeholder="Not provided"
                className="w-full h-10 px-3.5 bg-[#0b0c15] border border-[#1f213a] rounded-lg text-xs text-white focus:outline-none focus:border-indigo-500 transition-all placeholder:text-slate-600"
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
