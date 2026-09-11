import React from 'react';
import type { EvidenceItem } from '../../types/sop';

interface EvidencePanelProps {
  evidence: EvidenceItem[];
  onSeek: (timeSec: number) => void;
}

export const EvidencePanel: React.FC<EvidencePanelProps> = ({ evidence, onSeek }) => {
  const formatTime = (seconds?: number): string => {
    if (seconds === undefined) return '00:00';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div className="sop-card">
      <div className="sop-card-header">
        <div className="sop-card-title">
          <span>📹 Grounded Evidence Links</span>
        </div>
        <span style={{ fontSize: '0.72rem', color: 'var(--sop-text-muted)' }}>
          Click to seek video player
        </span>
      </div>

      <div className="sop-card-body" style={{ padding: '0.75rem' }}>
        {evidence.length === 0 ? (
          <div style={{ padding: '1rem', textAlign: 'center', color: 'var(--sop-text-muted)', fontSize: '0.78rem' }}>
            Evidence unavailable for this work step.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
            {evidence.map((item) => (
              <div
                key={item.id}
                onClick={() => {
                  if (item.timestamp_sec !== undefined) {
                    onSeek(item.timestamp_sec);
                  }
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.85rem',
                  padding: '0.65rem 0.85rem',
                  backgroundColor: 'var(--sop-bg-panel)',
                  border: '1px solid var(--sop-border)',
                  borderRadius: '6px',
                  cursor: item.timestamp_sec !== undefined ? 'pointer' : 'default',
                  transition: 'all 0.15s ease',
                }}
              >
                {/* Thumbnail / Timecode badge */}
                <div
                  style={{
                    width: '64px',
                    height: '42px',
                    backgroundColor: '#0a0d18',
                    border: '1px solid var(--sop-border-subtle)',
                    borderRadius: '4px',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}
                >
                  <span className="sop-mono" style={{ fontSize: '0.68rem', color: '#60a5fa', fontWeight: 700 }}>
                    {formatTime(item.timestamp_sec)}
                  </span>
                  <span style={{ fontSize: '0.55rem', color: 'var(--sop-text-muted)', textTransform: 'uppercase' }}>
                    {item.source}
                  </span>
                </div>

                {/* Evidence Content */}
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--sop-text-primary)' }}>
                    {item.claim}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--sop-text-secondary)', marginTop: '2px', lineHeight: 1.3 }}>
                    {item.observation}
                  </div>
                </div>

                {/* Seek Arrow */}
                {item.timestamp_sec !== undefined && (
                  <button
                    type="button"
                    className="sop-btn sop-btn-secondary"
                    style={{ padding: '0.25rem 0.5rem', fontSize: '0.7rem' }}
                    onClick={(e) => {
                      e.stopPropagation();
                      onSeek(item.timestamp_sec!);
                    }}
                  >
                    Seek ▶
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
