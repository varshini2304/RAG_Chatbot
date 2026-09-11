import React from 'react';
import type { AuditEvent } from '../../types/sop';

interface AuditTrailViewProps {
  auditTrail: AuditEvent[];
}

export const AuditTrailView: React.FC<AuditTrailViewProps> = ({ auditTrail }) => {
  return (
    <div className="sop-card">
      <div className="sop-card-header">
        <div className="sop-card-title">
          <span>🛡 Verification & Compliance Audit Trail</span>
        </div>
        <span style={{ fontSize: '0.72rem', color: 'var(--sop-text-muted)' }}>
          Immutable event log for quality management
        </span>
      </div>

      {auditTrail.length === 0 ? (
        <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--sop-text-muted)', fontSize: '0.8rem' }}>
          Audit history unavailable.
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table className="sop-table">
            <thead>
              <tr>
                <th style={{ width: '160px' }}>Timestamp</th>
                <th style={{ width: '160px' }}>Stage</th>
                <th style={{ width: '150px' }}>Actor</th>
                <th>Action Performed</th>
                <th style={{ width: '100px', textAlign: 'center' }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {auditTrail.map((ev) => {
                let statusColor = 'var(--sop-teal)';
                if (ev.status === 'skipped') statusColor = 'var(--sop-gray)';
                if (ev.status === 'pending') statusColor = 'var(--sop-amber)';

                return (
                  <tr key={ev.id}>
                    <td className="sop-mono" style={{ color: 'var(--sop-text-muted)' }}>
                      {ev.timestamp}
                    </td>
                    <td style={{ fontWeight: 600, color: 'var(--sop-text-secondary)' }}>
                      {ev.stage}
                    </td>
                    <td style={{ color: '#93c5fd', fontSize: '0.74rem' }}>
                      {ev.actor}
                    </td>
                    <td style={{ color: 'var(--sop-text-primary)' }}>
                      {ev.action}
                    </td>
                    <td style={{ textAlign: 'center', color: statusColor, fontWeight: 700 }}>
                      {ev.status.toUpperCase()}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
