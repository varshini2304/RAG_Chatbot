import React from 'react';
import type { WorkStep } from '../../types/sop';
import { StatusBadge } from '../common/StatusBadge';

interface WorkStepCardProps {
  step: WorkStep;
  isSelected: boolean;
  onSelect: (stepId: string) => void;
  onSeek: (startTime: number) => void;
}

export const WorkStepCard: React.FC<WorkStepCardProps> = ({
  step,
  isSelected,
  onSelect,
  onSeek,
}) => {
  const formatTime = (seconds: number): string => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div
      onClick={() => {
        onSelect(step.id);
        onSeek(step.start_time);
      }}
      style={{
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: isSelected ? 'var(--sop-bg-elevated)' : 'var(--sop-bg-surface)',
        border: '1px solid',
        borderColor: isSelected ? 'var(--sop-blue-border)' : 'var(--sop-border)',
        borderRadius: '8px',
        overflow: 'hidden',
        cursor: 'pointer',
        transition: 'all 0.15s ease',
        boxShadow: isSelected ? '0 0 0 1px #3b82f6' : 'none',
      }}
    >
      {/* Keyframe Thumbnail Container */}
      <div
        style={{
          position: 'relative',
          width: '100%',
          aspectRatio: '16/9',
          backgroundColor: '#0a0d17',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          overflow: 'hidden',
          borderBottom: '1px solid var(--sop-border-subtle)',
        }}
      >
        {/* Synthetic high-contrast keyframe canvas visual */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: `radial-gradient(circle at 50% 50%, #17203a 0%, #0c101c 100%)`,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <span style={{ fontSize: '1.25rem', opacity: 0.6 }}>⚙</span>
          <span className="sop-mono" style={{ fontSize: '0.65rem', color: '#64748b', marginTop: '4px' }}>
            FRAME @ {formatTime(step.start_time)}
          </span>
        </div>

        {/* Step Number Badge Overlay */}
        <div
          style={{
            position: 'absolute',
            top: '8px',
            left: '8px',
            backgroundColor: 'rgba(11, 13, 23, 0.85)',
            border: '1px solid var(--sop-border)',
            borderRadius: '4px',
            padding: '2px 6px',
            fontSize: '0.7rem',
            fontWeight: 700,
            color: '#93c5fd',
            backdropFilter: 'blur(2px)',
          }}
        >
          Step {step.step_number}
        </div>

        {/* Timestamp Range Overlay */}
        <div
          className="sop-mono"
          style={{
            position: 'absolute',
            bottom: '8px',
            right: '8px',
            backgroundColor: 'rgba(0, 0, 0, 0.75)',
            borderRadius: '4px',
            padding: '2px 6px',
            fontSize: '0.68rem',
            color: '#cbd5e1',
          }}
        >
          {formatTime(step.start_time)} – {formatTime(step.end_time)}
        </div>
      </div>

      {/* Card Body */}
      <div style={{ padding: '0.85rem' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '0.5rem', marginBottom: '0.4rem' }}>
          <h4 style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--sop-text-primary)', margin: 0, lineHeight: 1.3 }}>
            {step.title}
          </h4>
          <StatusBadge status={step.status} size="sm" />
        </div>

        {step.title_ja && (
          <p style={{ fontSize: '0.72rem', color: 'var(--sop-text-muted)', margin: '0 0 0.5rem 0', lineHeight: 1.3 }}>
            {step.title_ja}
          </p>
        )}

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--sop-text-muted)' }}>
          <span>{step.evidence.length} evidence links</span>
          <span style={{ color: '#60a5fa' }}>Inspect →</span>
        </div>
      </div>
    </div>
  );
};
