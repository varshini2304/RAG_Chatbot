import React from 'react';

interface ChartCardProps {
  title: string;
  selector?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  bodyClassName?: string;
}

export const ChartCard: React.FC<ChartCardProps> = ({
  title,
  selector,
  children,
  className,
  bodyClassName,
}) => {
  return (
    <div className={`enterprise-card flex h-[340px] flex-col overflow-hidden p-5 bg-[#161B2E] border border-white/[0.06] rounded-[18px] ${className || ''}`}>
      <div className="mb-3 flex flex-shrink-0 items-center justify-between gap-2">
        <h3 className="font-outfit text-base sm:text-[17px] font-bold tracking-tight text-[#F8FAFC] whitespace-nowrap">{title}</h3>
        {selector ? <div className="relative z-20 flex-shrink-0">{selector}</div> : null}
      </div>
      <div className={`relative min-h-0 w-full flex-1 ${bodyClassName || ''}`}>
        {children}
      </div>
    </div>
  );
};
