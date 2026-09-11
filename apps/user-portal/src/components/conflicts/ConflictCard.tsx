import React, { useState } from 'react';
import type { ConflictItem } from '../../types/sop';

interface ConflictCardProps {
  conflict: ConflictItem;
  onResolve: (
    conflictId: string,
    resolution: 'video' | 'manual' | 'merge' | 'escalate',
    comment: string
  ) => Promise<void>;
  onSeek: (timeSec: number) => void;
}

export const ConflictCard: React.FC<ConflictCardProps> = ({
  conflict,
  onResolve,
  onSeek,
}) => {
  const [selectedResolution, setSelectedResolution] = useState<'video' | 'manual' | 'merge' | 'escalate'>(
    conflict.resolution || 'manual'
  );
  const [comment, setComment] = useState(conflict.resolution_comment || '');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!comment.trim()) {
      setError('A justification comment is strictly required to resolve a safety-critical conflict.');
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      await onResolve(conflict.id, selectedResolution, comment.trim());
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      style={{
        backgroundColor: 'var(--sop-bg-surface)',
        border: '1px solid',
        borderColor: conflict.resolved ? 'var(--sop-teal-border)' : 'var(--sop-red-border)',
        borderRadius: '8px',
        overflow: 'hidden',
      }}
    >
      {/* Top Banner Alert */}
      <div
        style={{
          padding: '0.85rem 1.15rem',
          backgroundColor: conflict.resolved ? 'var(--sop-teal-bg)' : 'var(--sop-red-bg)',
          borderBottom: '1px solid',
          borderColor: conflict.resolved ? 'var(--sop-teal-border)' : 'var(--sop-red-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <span style={{ fontSize: '1.1rem' }}>{conflict.resolved ? '✓' : '⚠'}</span>
          <div>
            <h3
              style={{
                fontSize: '0.88rem',
                fontWeight: 700,
                color: conflict.resolved ? 'var(--sop-teal)' : 'var(--sop-red)',
                margin: 0,
              }}
            >
              {conflict.resolved ? 'Conflict Resolved' : 'Safety-Critical Discrepancy Detected'}
            </h3>
            <span style={{ fontSize: '0.72rem', color: 'var(--sop-text-secondary)' }}>
              Step {conflict.step_number}: {conflict.step_title}
            </span>
          </div>
        </div>

        {conflict.resolved && (
          <span className="sop-badge sop-badge-teal">
            Resolved: {conflict.resolution?.toUpperCase()}
          </span>
        )}
      </div>

      {/* Difference Description Callout */}
      <div
        style={{
          padding: '0.85rem 1.15rem',
          backgroundColor: 'var(--sop-bg-panel)',
          borderBottom: '1px solid var(--sop-border)',
        }}
      >
        <div style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--sop-amber)', marginBottom: '0.25rem' }}>
          Documented Discrepancy
        </div>
        <p style={{ fontSize: '0.8rem', color: 'var(--sop-text-primary)', margin: 0, lineHeight: 1.4 }}>
          {conflict.difference}
        </p>
      </div>

      {/* Side-by-Side Comparison */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1px', backgroundColor: 'var(--sop-border)' }}>
        {/* Left Column: Video Evidence */}
        <div style={{ backgroundColor: 'var(--sop-bg-surface)', padding: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#93c5fd', textTransform: 'uppercase' }}>
              📹 Video Evidence (AI Extracted)
            </span>
            <button
              type="button"
              className="sop-btn sop-btn-secondary"
              style={{ padding: '0.2rem 0.5rem', fontSize: '0.68rem' }}
              onClick={() => onSeek(conflict.video_evidence.timestamp_sec)}
            >
              Seek to {Math.floor(conflict.video_evidence.timestamp_sec / 60)}:{(conflict.video_evidence.timestamp_sec % 60).toString().padStart(2, '0')} ▶
            </button>
          </div>

          <div style={{ fontSize: '0.78rem', color: 'var(--sop-text-primary)', marginBottom: '0.5rem', lineHeight: 1.4 }}>
            <strong>Observed Action:</strong> {conflict.video_evidence.observed_action}
          </div>

          <div style={{ fontSize: '0.75rem', color: 'var(--sop-text-secondary)' }}>
            <strong>Detected Tools:</strong>
            <ul style={{ margin: '0.25rem 0 0 1.2rem', padding: 0 }}>
              {conflict.video_evidence.detected_tools.map((t, idx) => (
                <li key={idx} style={{ color: '#fca5a5' }}>{t}</li>
              ))}
            </ul>
          </div>
        </div>

        {/* Right Column: Reference Manual */}
        <div style={{ backgroundColor: 'var(--sop-bg-surface)', padding: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#34d399', textTransform: 'uppercase' }}>
              📄 Reference Manual Specification
            </span>
            <span className="sop-mono" style={{ fontSize: '0.7rem', color: 'var(--sop-text-muted)' }}>
              Page {conflict.reference_manual.page_number}
            </span>
          </div>

          <div style={{ fontSize: '0.78rem', color: 'var(--sop-text-primary)', marginBottom: '0.5rem', lineHeight: 1.4 }}>
            <strong>Document:</strong> {conflict.reference_manual.document_name}
          </div>

          <div style={{ fontSize: '0.78rem', color: 'var(--sop-text-secondary)', marginBottom: '0.5rem', lineHeight: 1.4 }}>
            <strong>Instruction:</strong> {conflict.reference_manual.relevant_instruction}
          </div>

          <div style={{ fontSize: '0.75rem', color: 'var(--sop-text-secondary)' }}>
            <strong>Mandated Tools:</strong>
            <ul style={{ margin: '0.25rem 0 0 1.2rem', padding: 0 }}>
              {conflict.reference_manual.required_tools.map((t, idx) => (
                <li key={idx} style={{ color: '#86efac' }}>{t}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* Resolution Section */}
      <div style={{ padding: '1.15rem', backgroundColor: 'var(--sop-bg-panel)', borderTop: '1px solid var(--sop-border)' }}>
        {conflict.resolved ? (
          <div>
            <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--sop-teal)', marginBottom: '0.35rem' }}>
              Resolution Confirmed ({conflict.resolved_at})
            </div>
            <p style={{ fontSize: '0.78rem', color: 'var(--sop-text-secondary)', margin: 0 }}>
              <strong>Decision:</strong> {conflict.resolution?.toUpperCase()} — {conflict.resolution_comment}
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
            <div style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--sop-text-primary)' }}>
              Select Explicit Resolution:
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.65rem' }}>
              {[
                { key: 'manual', label: 'Use Reference Manual', desc: 'Enforces calibrated torque specification' },
                { key: 'video', label: 'Use Video Evidence', desc: 'Adopts operator field practice' },
                { key: 'merge', label: 'Merge Both Sources', desc: 'Combines video motion with manual torque' },
                { key: 'escalate', label: 'Escalate to Engineering', desc: 'Flags for formal peer review' },
              ].map((opt) => (
                <label
                  key={opt.key}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '0.5rem',
                    padding: '0.65rem',
                    borderRadius: '6px',
                    backgroundColor: selectedResolution === opt.key ? 'var(--sop-bg-elevated)' : 'var(--sop-bg-surface)',
                    border: '1px solid',
                    borderColor: selectedResolution === opt.key ? 'var(--sop-blue-border)' : 'var(--sop-border)',
                    cursor: 'pointer',
                  }}
                >
                  <input
                    type="radio"
                    name={`conflict_${conflict.id}`}
                    value={opt.key}
                    checked={selectedResolution === opt.key}
                    onChange={() => setSelectedResolution(opt.key as 'video' | 'manual' | 'merge' | 'escalate')}
                    style={{ marginTop: '2px', accentColor: '#3b82f6' }}
                  />
                  <div>
                    <div style={{ fontSize: '0.76rem', fontWeight: 600, color: 'var(--sop-text-primary)' }}>
                      {opt.label}
                    </div>
                    <div style={{ fontSize: '0.68rem', color: 'var(--sop-text-muted)', marginTop: '2px' }}>
                      {opt.desc}
                    </div>
                  </div>
                </label>
              ))}
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--sop-text-secondary)', marginBottom: '0.35rem' }}>
                Engineering Justification Comment (Mandatory)
              </label>
              <textarea
                rows={2}
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Explain why this resolution was selected for audit compliance..."
                style={{
                  width: '100%',
                  padding: '0.5rem 0.75rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--sop-bg-root)',
                  border: '1px solid var(--sop-border)',
                  color: 'var(--sop-text-primary)',
                  fontSize: '0.78rem',
                  resize: 'vertical',
                }}
              />
            </div>

            {error && (
              <div style={{ color: '#f87171', fontSize: '0.74rem' }}>
                {error}
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button
                type="submit"
                className="sop-btn sop-btn-primary"
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Recording Resolution...' : 'Confirm Resolution & Update Step'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
