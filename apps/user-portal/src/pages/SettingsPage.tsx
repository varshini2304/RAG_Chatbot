import React from 'react';

export const SettingsPage: React.FC = () => {
  const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL as string) || 'http://localhost:8000/api/v1';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div className="sop-card" style={{ padding: '1rem 1.25rem', backgroundColor: 'var(--sop-bg-panel)' }}>
        <h2 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--sop-text-primary)', margin: 0 }}>
          System Configuration & Runtime Settings
        </h2>
        <span style={{ fontSize: '0.74rem', color: 'var(--sop-text-secondary)' }}>
          FastAPI backend connectivity, AI pipeline configuration, and environment parameters
        </span>
      </div>

      <div className="sop-card">
        <div className="sop-card-header">
          <div className="sop-card-title">
            <span>🌐 Backend API Endpoint</span>
          </div>
          <span className="sop-badge sop-badge-teal">Active</span>
        </div>

        <div className="sop-card-body">
          <table className="sop-table">
            <tbody>
              <tr>
                <td style={{ width: '180px', fontWeight: 600, color: 'var(--sop-text-secondary)' }}>VITE_API_BASE_URL</td>
                <td className="sop-mono" style={{ color: '#93c5fd' }}>{apiBaseUrl}</td>
              </tr>
              <tr>
                <td style={{ fontWeight: 600, color: 'var(--sop-text-secondary)' }}>Authentication Scheme</td>
                <td>JSON Web Token (Bearer Header via HTTP Authorization)</td>
              </tr>
              <tr>
                <td style={{ fontWeight: 600, color: 'var(--sop-text-secondary)' }}>Max Video Upload Size</td>
                <td className="sop-mono">2048 MB (2.0 GB)</td>
              </tr>
              <tr>
                <td style={{ fontWeight: 600, color: 'var(--sop-text-secondary)' }}>Video Duration Limit</td>
                <td className="sop-mono">7200.0s (2 Hours)</td>
              </tr>
              <tr>
                <td style={{ fontWeight: 600, color: 'var(--sop-text-secondary)' }}>ASR Engine Baseline</td>
                <td>Faster-Whisper (base / int8 / CPU inference)</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
