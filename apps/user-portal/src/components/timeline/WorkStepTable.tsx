import React from 'react';
import type { WorkStep } from '../../types/sop';
import { StatusBadge } from '../common/StatusBadge';

interface WorkStepTableProps {
  steps: WorkStep[];
  selectedStepId: string;
  onSelect: (stepId: string) => void;
  onSeek: (timeSec: number) => void;
}

export const WorkStepTable: React.FC<WorkStepTableProps> = ({
  steps,
  selectedStepId,
  onSelect,
  onSeek,
}) => {
  const formatTime = (seconds: number): string => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div className="sop-card">
      <div style={{ overflowX: 'auto' }}>
        <table className="sop-table">
          <thead>
            <tr>
              <th style={{ width: '60px' }}>Step</th>
              <th style={{ width: '120px' }}>Range</th>
              <th>English Instruction</th>
              <th>日本語の手順</th>
              <th style={{ width: '130px' }}>Tools Required</th>
              <th style={{ width: '110px' }}>Status</th>
              <th style={{ width: '90px', textAlign: 'right' }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {steps.map((step) => {
              const isSelected = step.id === selectedStepId;
              return (
                <tr
                  key={step.id}
                  style={{
                    backgroundColor: isSelected ? 'var(--sop-bg-elevated)' : 'transparent',
                    cursor: 'pointer',
                  }}
                  onClick={() => {
                    onSelect(step.id);
                    onSeek(step.start_time);
                  }}
                >
                  <td style={{ fontWeight: 700, color: '#93c5fd' }}>
                    #{step.step_number}
                  </td>
                  <td className="sop-mono" style={{ color: 'var(--sop-text-secondary)' }}>
                    {formatTime(step.start_time)} – {formatTime(step.end_time)}
                  </td>
                  <td style={{ fontWeight: 600, color: 'var(--sop-text-primary)' }}>
                    {step.title}
                  </td>
                  <td style={{ color: 'var(--sop-text-secondary)' }}>
                    {step.title_ja || <span style={{ color: 'var(--sop-text-muted)', fontStyle: 'italic' }}>—</span>}
                  </td>
                  <td style={{ fontSize: '0.72rem', color: 'var(--sop-text-muted)' }}>
                    {step.tools_required && step.tools_required.length > 0
                      ? step.tools_required[0] + (step.tools_required.length > 1 ? ` (+${step.tools_required.length - 1})` : '')
                      : 'None'}
                  </td>
                  <td>
                    <StatusBadge status={step.status} size="sm" />
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <button
                      type="button"
                      className="sop-btn sop-btn-secondary"
                      style={{ padding: '0.25rem 0.55rem', fontSize: '0.7rem' }}
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelect(step.id);
                        onSeek(step.start_time);
                      }}
                    >
                      Seek ▶
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
