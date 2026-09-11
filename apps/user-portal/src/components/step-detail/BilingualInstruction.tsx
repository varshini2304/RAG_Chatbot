import React from 'react';
import type { WorkStep } from '../../types/sop';

interface BilingualInstructionProps {
  step: WorkStep;
}

export const BilingualInstruction: React.FC<BilingualInstructionProps> = ({ step }) => {
  return (
    <div className="sop-card">
      <div className="sop-card-header">
        <div className="sop-card-title">
          <span>🌐 Bilingual Operational Instructions</span>
        </div>
        <span style={{ fontSize: '0.72rem', color: 'var(--sop-text-muted)' }}>
          Side-by-side technical alignment
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1px', backgroundColor: 'var(--sop-border)' }}>
        {/* English Column */}
        <div style={{ backgroundColor: 'var(--sop-bg-surface)', padding: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#93c5fd', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              English (EN)
            </span>
          </div>
          <h4 style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--sop-text-primary)', margin: '0 0 0.5rem 0' }}>
            {step.title}
          </h4>
          <p style={{ fontSize: '0.78rem', color: 'var(--sop-text-secondary)', lineHeight: 1.45, margin: 0 }}>
            {step.description}
          </p>
        </div>

        {/* Japanese Column */}
        <div style={{ backgroundColor: 'var(--sop-bg-surface)', padding: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#34d399', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              日本語 (JA)
            </span>
          </div>
          {step.title_ja ? (
            <>
              <h4 style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--sop-text-primary)', margin: '0 0 0.5rem 0' }}>
                {step.title_ja}
              </h4>
              <p style={{ fontSize: '0.78rem', color: 'var(--sop-text-secondary)', lineHeight: 1.45, margin: 0 }}>
                {step.description_ja || '日本語の説明はありません'}
              </p>
            </>
          ) : (
            <div style={{ fontSize: '0.78rem', color: 'var(--sop-text-muted)', fontStyle: 'italic', padding: '1rem 0' }}>
              Japanese translation unavailable for this work step.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
