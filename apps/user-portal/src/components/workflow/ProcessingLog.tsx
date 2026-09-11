import React from 'react';
import type { ProcessingLogEntry } from '../../types/sop';

interface ProcessingLogProps {
  logs: ProcessingLogEntry[];
}

export const ProcessingLog: React.FC<ProcessingLogProps> = ({ logs }) => {
  return (
    <div className="sop-card" style={{ display: 'flex', flexDirection: 'column' }}>
      <div className="sop-card-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <span style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--sop-text-primary)' }}>
            Processing Log
          </span>
          <span
            style={{
              fontSize: '0.65rem',
              fontWeight: 700,
              padding: '2px 6px',
              borderRadius: '4px',
              backgroundColor: 'rgba(16, 185, 129, 0.15)',
              color: '#10b981',
              border: '1px solid rgba(16, 185, 129, 0.35)',
              letterSpacing: '0.04em',
              textTransform: 'uppercase',
            }}
          >
            Live
          </span>
        </div>

        <button
          type="button"
          className="sop-btn-link"
          onClick={() => {}}
          style={{
            fontSize: '0.72rem',
            color: '#60a5fa',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            padding: 0,
            display: 'flex',
            alignItems: 'center',
            gap: '0.25rem',
          }}
        >
          View Full Log →
        </button>
      </div>

      <div style={{ overflowX: 'auto', flex: 1 }}>
        <table className="sop-table" style={{ width: '100%' }}>
          <thead>
            <tr>
              <th style={{ width: '85px' }}>Time</th>
              <th style={{ width: '150px' }}>Stage</th>
              <th>Message</th>
              <th style={{ width: '70px', textAlign: 'center' }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => {
              const isSuccess = log.status === 'success';
              const isProcessing = log.status === 'processing';
              const isWarning = log.status === 'warning';
              const isError = log.status === 'error';

              return (
                <tr key={log.id}>
                  <td className="sop-mono" style={{ color: 'var(--sop-text-muted)', fontSize: '0.72rem' }}>
                    {log.timestamp}
                  </td>
                  <td style={{ fontWeight: 600, color: 'var(--sop-text-secondary)', fontSize: '0.74rem' }}>
                    {log.stage}
                  </td>
                  <td style={{ color: 'var(--sop-text-primary)', fontSize: '0.76rem' }}>
                    {log.message}
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    {isSuccess && (
                      <span
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          width: '18px',
                          height: '18px',
                          borderRadius: '50%',
                          backgroundColor: 'rgba(16, 185, 129, 0.15)',
                          color: '#10b981',
                          fontSize: '0.72rem',
                          fontWeight: 700,
                        }}
                      >
                        ✓
                      </span>
                    )}
                    {isProcessing && (
                      <span
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          width: '18px',
                          height: '18px',
                          borderRadius: '50%',
                          border: '2px solid #3b82f6',
                          borderTopColor: 'transparent',
                          animation: 'sop-spin 1s linear infinite',
                        }}
                      />
                    )}
                    {isWarning && (
                      <span
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          width: '18px',
                          height: '18px',
                          borderRadius: '50%',
                          backgroundColor: 'rgba(245, 158, 11, 0.15)',
                          color: '#f59e0b',
                          fontSize: '0.72rem',
                          fontWeight: 700,
                        }}
                      >
                        ⚠
                      </span>
                    )}
                    {isError && (
                      <span
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          width: '18px',
                          height: '18px',
                          borderRadius: '50%',
                          backgroundColor: 'rgba(239, 68, 68, 0.15)',
                          color: '#ef4444',
                          fontSize: '0.72rem',
                          fontWeight: 700,
                        }}
                      >
                        ✕
                      </span>
                    )}
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
