import React from 'react';

interface ProgressBarProps {
  label: string;
  value: number;
  color?: string;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({ label, value, color = 'bg-indigo-500' }) => {
  return (
    <div className="space-y-1 w-full">
      <div className="flex items-center justify-between text-[11px] font-semibold">
        <span className="text-[#94a3b8]">{label}</span>
        <span className="text-white">{value}%</span>
      </div>
      <div className="w-full h-1.5 bg-[#1f213a] rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all duration-500`} style={{ width: `${value}%` }} />
      </div>
    </div>
  );
};
