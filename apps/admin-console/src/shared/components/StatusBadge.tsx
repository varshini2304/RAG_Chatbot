import React from 'react';

const clsx = (...classes: (string | undefined | false | null)[]) => classes.filter(Boolean).join(' ');

interface StatusBadgeProps {
  status: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const s = status.toLowerCase();
  
  let bg = 'bg-slate-500/15 text-slate-400';
  if (['online', 'resolved', 'healthy', 'active', 'connected', 'running'].includes(s)) {
    bg = 'bg-success/15 text-[#4ade80]';
  } else if (['offline', 'failed', 'unhealthy', 'disconnected'].includes(s)) {
    bg = 'bg-danger/15 text-danger';
  } else if (['degraded', 'retrying', 'warning', 'inactive'].includes(s)) {
    bg = 'bg-warning/15 text-[#fcd34d]';
  }

  return (
    <span className={clsx("inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider", bg)}>
      {status}
    </span>
  );
};
