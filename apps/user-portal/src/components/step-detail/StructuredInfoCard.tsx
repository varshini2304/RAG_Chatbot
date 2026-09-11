import React from 'react';
import type { WorkStep } from '../../types/sop';

interface StructuredInfoCardProps {
  step: WorkStep;
}

export const StructuredInfoCard: React.FC<StructuredInfoCardProps> = ({ step }) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Tools Required Section */}
      <div className="sop-card">
        <div className="sop-card-header" style={{ padding: '0.65rem 1rem' }}>
          <div className="sop-card-title" style={{ fontSize: '0.8rem' }}>
            <span>🔧 Tools Required</span>
          </div>
        </div>
        <div className="sop-card-body" style={{ padding: '0.85rem 1rem' }}>
          {step.tools_required && step.tools_required.length > 0 ? (
            <ul style={{ margin: 0, paddingLeft: '1.2rem', fontSize: '0.78rem', color: 'var(--sop-text-primary)' }}>
              {step.tools_required.map((tool, idx) => (
                <li key={idx} style={{ marginBottom: '0.35rem' }}>
                  {tool}
                </li>
              ))}
            </ul>
          ) : (
            <span style={{ fontSize: '0.78rem', color: 'var(--sop-text-muted)', fontStyle: 'italic' }}>
              None required for this step
            </span>
          )}
        </div>
      </div>

      {/* PPE Required Section */}
      <div className="sop-card">
        <div className="sop-card-header" style={{ padding: '0.65rem 1rem' }}>
          <div className="sop-card-title" style={{ fontSize: '0.8rem' }}>
            <span>🦺 PPE Required</span>
          </div>
        </div>
        <div className="sop-card-body" style={{ padding: '0.85rem 1rem' }}>
          {step.ppe_required && step.ppe_required.length > 0 ? (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
              {step.ppe_required.map((ppe, idx) => (
                <span
                  key={idx}
                  style={{
                    backgroundColor: 'var(--sop-bg-elevated)',
                    border: '1px solid var(--sop-border)',
                    borderRadius: '4px',
                    padding: '0.25rem 0.6rem',
                    fontSize: '0.74rem',
                    color: 'var(--sop-text-secondary)',
                  }}
                >
                  🛡 {ppe}
                </span>
              ))}
            </div>
          ) : (
            <span style={{ fontSize: '0.78rem', color: 'var(--sop-text-muted)', fontStyle: 'italic' }}>
              Standard shop safety attire
            </span>
          )}
        </div>
      </div>

      {/* Safety Warnings Section (Safety Critical Alert) */}
      <div
        style={{
          backgroundColor: 'var(--sop-amber-bg)',
          border: '1px solid var(--sop-amber-border)',
          borderRadius: '8px',
          padding: '0.85rem 1rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
          <span style={{ color: 'var(--sop-amber)', fontWeight: 700, fontSize: '0.85rem' }}>
            ⚠ Safety Warnings
          </span>
        </div>
        {step.safety_warnings && step.safety_warnings.length > 0 ? (
          <ul style={{ margin: 0, paddingLeft: '1.2rem', fontSize: '0.76rem', color: '#fde68a', lineHeight: 1.45 }}>
            {step.safety_warnings.map((warn, idx) => (
              <li key={idx} style={{ marginBottom: '0.35rem' }}>
                {warn}
              </li>
            ))}
          </ul>
        ) : (
          <span style={{ fontSize: '0.75rem', color: 'var(--sop-text-muted)', fontStyle: 'italic' }}>
            No specific safety hazards flagged for this step
          </span>
        )}
      </div>

      {/* Quality Checkpoints Section */}
      <div className="sop-card">
        <div className="sop-card-header" style={{ padding: '0.65rem 1rem' }}>
          <div className="sop-card-title" style={{ fontSize: '0.8rem' }}>
            <span>🔍 Quality Checkpoints</span>
          </div>
        </div>
        <div className="sop-card-body" style={{ padding: '0.85rem 1rem' }}>
          {step.quality_checkpoints && step.quality_checkpoints.length > 0 ? (
            <ul style={{ margin: 0, paddingLeft: '1.2rem', fontSize: '0.78rem', color: 'var(--sop-text-primary)' }}>
              {step.quality_checkpoints.map((check, idx) => (
                <li key={idx} style={{ marginBottom: '0.35rem' }}>
                  {check}
                </li>
              ))}
            </ul>
          ) : (
            <span style={{ fontSize: '0.78rem', color: 'var(--sop-text-muted)', fontStyle: 'italic' }}>
              No critical inspection points specified
            </span>
          )}
        </div>
      </div>

      {/* Expected Outcome Section */}
      <div className="sop-card">
        <div className="sop-card-header" style={{ padding: '0.65rem 1rem' }}>
          <div className="sop-card-title" style={{ fontSize: '0.8rem' }}>
            <span>🎯 Expected Outcome</span>
          </div>
        </div>
        <div className="sop-card-body" style={{ padding: '0.85rem 1rem', fontSize: '0.78rem', color: 'var(--sop-text-primary)' }}>
          {step.expected_outcome ? (
            <p style={{ margin: 0, lineHeight: 1.4 }}>{step.expected_outcome}</p>
          ) : (
            <span style={{ color: 'var(--sop-text-muted)', fontStyle: 'italic' }}>
              Outcome criteria not documented
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
