import React from 'react';
import type { LucideIcon } from 'lucide-react';

const clsx = (...classes: (string | undefined | false | null)[]) => classes.filter(Boolean).join(' ');

interface MetricCardProps {
  title: string;
  value: string | number;
  change?: string;
  trend?: 'up' | 'down';
  trendType?: 'positive' | 'negative';
  icon: LucideIcon;
  iconBg: string;
  iconColor: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  icon: Icon,
  iconBg,
  iconColor,
}) => {
  return (
    <div className="enterprise-card group flex h-[145px] flex-col justify-between overflow-hidden p-5 bg-[#161B2E] border border-white/[0.06] rounded-[18px]">
      {/* Top Section: Icon & Title */}
      <div className="flex items-center gap-2.5">
        <div className={clsx('flex h-9 w-9 items-center justify-center rounded-xl border border-white/10 shadow-md flex-shrink-0', iconBg)}>
          <Icon className={clsx('h-4.5 w-4.5', iconColor)} />
        </div>
        <span className="text-[11px] font-bold text-[#94A3B8] uppercase tracking-wide leading-tight min-w-0 flex-1">{title}</span>
      </div>

      {/* Bottom Section: Large Metric */}
      <div className="mt-2">
        <span className="block font-outfit text-[38px] font-black leading-none tracking-tight text-[#F8FAFC]">
          {value}
        </span>
      </div>
    </div>
  );
};
