import React, { useEffect, useState } from 'react';
import type { VideoMetadata } from '../../types/sop';

interface TopBarProps {
  title: string;
  breadcrumb?: string[];
  video?: VideoMetadata;
  activeDatasetType: 'standard' | 'silent';
  onSwitchDataset: (type: 'standard' | 'silent') => void;
  username: string;
}

export const TopBar: React.FC<TopBarProps> = ({
  title,
  breadcrumb = [],
  video,
  activeDatasetType,
  onSwitchDataset,
  username,
}) => {
  const [timeStr, setTimeStr] = useState<string>('10 Sep 2026 10:24');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const day = now.getDate();
      const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      const month = months[now.getMonth()];
      const year = now.getFullYear();
      const hours = now.getHours().toString().padStart(2, '0');
      const mins = now.getMinutes().toString().padStart(2, '0');
      setTimeStr(`${day} ${month} ${year} ${hours}:${mins}`);
    };
    updateTime();
    const interval = setInterval(updateTime, 60000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="sop-topbar">
      <div className="sop-topbar-left">
        <div>
          <div className="sop-page-title">
            <span>{title}</span>
            {video && (
              <span
                className="sop-mono"
                style={{
                  fontSize: '0.72rem',
                  fontWeight: 500,
                  color: 'var(--sop-text-secondary)',
                  backgroundColor: 'var(--sop-bg-root)',
                  border: '1px solid var(--sop-border)',
                  borderRadius: '4px',
                  padding: '2px 6px',
                }}
              >
                {video.filename}
              </span>
            )}
          </div>

          {breadcrumb.length > 0 && (
            <div className="sop-breadcrumb">
              {breadcrumb.map((crumb, idx) => (
                <React.Fragment key={idx}>
                  <span>{crumb}</span>
                  {idx < breadcrumb.length - 1 && <span>/</span>}
                </React.Fragment>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="sop-topbar-right">
        {/* Workflow Mode Switcher */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <span style={{ fontSize: '0.7rem', color: 'var(--sop-text-muted)' }}>Workflow Mode:</span>
          <div className="sop-mode-toggle">
            <button
              type="button"
              className={`sop-mode-btn ${activeDatasetType === 'standard' ? 'active' : ''}`}
              onClick={() => onSwitchDataset('standard')}
              title="Standard Demonstration with AAC audio stream and speech transcription"
            >
              Standard Audio (const_01)
            </button>
            <button
              type="button"
              className={`sop-mode-btn ${activeDatasetType === 'silent' ? 'active' : ''}`}
              onClick={() => onSwitchDataset('silent')}
              title="Silent Cleanroom recording without audio"
            >
              Silent Video (Cleanroom)
            </button>
          </div>
        </div>

        {/* Date & Time display matching Image 2 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', borderLeft: '1px solid var(--sop-border)', paddingLeft: '0.85rem' }}>
          <span style={{ fontSize: '0.9rem', cursor: 'pointer' }} title="Alerts & Notifications">
            🔔
          </span>

          <span className="sop-mono" style={{ fontSize: '0.72rem', color: 'var(--sop-text-secondary)' }}>
            {timeStr}
          </span>

          {/* User Badge */}
          <div
            style={{
              width: '28px',
              height: '28px',
              borderRadius: '6px',
              backgroundColor: '#3b82f6',
              color: '#fff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '0.75rem',
              fontWeight: 700,
            }}
            title={`Logged in as ${username}`}
          >
            {username.slice(0, 2).toUpperCase()}
          </div>
        </div>
      </div>
    </header>
  );
};
