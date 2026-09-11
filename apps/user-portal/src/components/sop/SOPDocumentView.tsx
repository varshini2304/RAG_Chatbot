import React from 'react';
import type { SOPDocument } from '../../types/sop';

interface SOPDocumentViewProps {
  document: SOPDocument;
  langView?: 'bilingual' | 'en' | 'ja';
}

export const SOPDocumentView: React.FC<SOPDocumentViewProps> = ({
  document,
  langView = 'bilingual',
}) => {
  return (
    <div
      className="sop-card"
      style={{
        backgroundColor: '#ffffff',
        color: '#0f172a',
        padding: '2.5rem',
        borderRadius: '6px',
        boxShadow: '0 4px 25px rgba(0,0,0,0.3)',
      }}
    >
      {/* Official Header Table matching Image 3 Screen 6 */}
      <div style={{ borderBottom: '2px solid #0f172a', paddingBottom: '1.25rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '140px 1fr 240px', alignItems: 'center', gap: '1.5rem' }}>
          {/* Logo placeholder */}
          <div
            style={{
              padding: '0.75rem',
              backgroundColor: '#f1f5f9',
              borderRadius: '4px',
              border: '1px solid #cbd5e1',
              textAlign: 'center',
              fontSize: '0.72rem',
              fontWeight: 700,
              color: '#3b82f6',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <span style={{ fontSize: '1.2rem', marginBottom: '2px' }}>🔷</span>
            <span>Your Company</span>
            <span style={{ fontSize: '0.65rem', color: '#64748b' }}>Logo</span>
          </div>

          {/* Title in Center */}
          <div style={{ textAlign: 'center' }}>
            <h1 style={{ fontSize: '1.35rem', fontWeight: 800, color: '#0f172a', margin: 0, letterSpacing: '0.02em' }}>
              Standard Operating Procedure (SOP)
            </h1>
            <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#475569', margin: '4px 0 0 0' }}>
              標準作業手順書
            </h2>
          </div>

          {/* Metadata Box on Right */}
          <div
            style={{
              border: '1px solid #cbd5e1',
              borderRadius: '4px',
              padding: '0.5rem 0.75rem',
              fontSize: '0.72rem',
              backgroundColor: '#f8fafc',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
              <strong style={{ color: '#475569' }}>Document ID:</strong>
              <span className="sop-mono" style={{ fontWeight: 600, color: '#0f172a' }}>SOP-2026-001</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
              <strong style={{ color: '#475569' }}>Version:</strong>
              <span style={{ color: '#0f172a' }}>1.0</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
              <strong style={{ color: '#475569' }}>Date:</strong>
              <span style={{ color: '#0f172a' }}>10/09/2026</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <strong style={{ color: '#475569' }}>Approved By:</strong>
              <span style={{ color: '#0f172a' }}>Engineering Team</span>
            </div>
          </div>
        </div>

        {/* SOP Procedure Title */}
        <div style={{ textAlign: 'center', marginTop: '1.25rem', paddingTop: '0.75rem', borderTop: '1px solid #e2e8f0' }}>
          <h3 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#1e293b', margin: 0 }}>
            Machine Operation and Maintenance
          </h3>
          <h4 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#64748b', margin: '3px 0 0 0' }}>
            機械の操作およびメンテナンス
          </h4>
        </div>
      </div>

      {/* Structured Step Table matching Image 3 Screen 6 */}
      <table
        style={{
          width: '100%',
          borderCollapse: 'collapse',
          fontSize: '0.82rem',
          textAlign: 'left',
          border: '1px solid #cbd5e1',
        }}
      >
        <thead>
          <tr style={{ backgroundColor: '#f1f5f9', borderBottom: '2px solid #cbd5e1' }}>
            <th style={{ width: '45px', padding: '0.75rem 0.6rem', color: '#334155', fontWeight: 700, borderRight: '1px solid #cbd5e1', textAlign: 'center' }}>
              Step
            </th>
            <th style={{ width: '110px', padding: '0.75rem 0.6rem', color: '#334155', fontWeight: 700, borderRight: '1px solid #cbd5e1', textAlign: 'center' }}>
              Image
            </th>
            {(langView === 'bilingual' || langView === 'en') && (
              <th style={{ padding: '0.75rem 0.85rem', color: '#334155', fontWeight: 700, borderRight: langView === 'bilingual' ? '1px solid #cbd5e1' : 'none' }}>
                English Instructions
              </th>
            )}
            {(langView === 'bilingual' || langView === 'ja') && (
              <th style={{ padding: '0.75rem 0.85rem', color: '#334155', fontWeight: 700 }}>
                日本語の手順
              </th>
            )}
          </tr>
        </thead>
        <tbody>
          {document.steps.map((step) => (
            <tr key={step.id} style={{ borderBottom: '1px solid #e2e8f0' }}>
              {/* Step # */}
              <td style={{ verticalAlign: 'top', padding: '0.85rem 0.5rem', fontWeight: 800, color: '#1e3a8a', textAlign: 'center', borderRight: '1px solid #e2e8f0' }}>
                {step.step_number}
              </td>

              {/* Keyframe Thumbnail */}
              <td style={{ verticalAlign: 'top', padding: '0.85rem 0.5rem', textAlign: 'center', borderRight: '1px solid #e2e8f0' }}>
                <div
                  style={{
                    width: '90px',
                    height: '56px',
                    backgroundColor: '#1e293b',
                    borderRadius: '4px',
                    margin: '0 auto',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#fff',
                    fontSize: '0.65rem',
                    fontFamily: 'var(--sop-font-mono)',
                    border: '1px solid #334155',
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      width: '18px',
                      height: '18px',
                      borderRadius: '50%',
                      backgroundColor: step.step_number === 3 ? '#ef4444' : (step.step_number === 4 ? '#f59e0b' : '#3b82f6'),
                    }}
                  />
                </div>
              </td>

              {/* English Instructions */}
              {(langView === 'bilingual' || langView === 'en') && (
                <td style={{ verticalAlign: 'top', padding: '0.85rem', color: '#1e293b', borderRight: langView === 'bilingual' ? '1px solid #e2e8f0' : 'none' }}>
                  <div style={{ fontWeight: 700, color: '#0f172a', marginBottom: '0.35rem' }}>
                    {step.title}
                  </div>
                  <p style={{ margin: 0, lineHeight: 1.45, color: '#334155' }}>
                    {step.description}
                  </p>
                  {step.ppe_required && step.ppe_required.length > 0 && (
                    <div style={{ fontSize: '0.72rem', color: '#0369a1', marginTop: '0.35rem' }}>
                      <strong>PPE:</strong> {step.ppe_required.join(', ')}
                    </div>
                  )}
                </td>
              )}

              {/* Japanese Instructions */}
              {(langView === 'bilingual' || langView === 'ja') && (
                <td style={{ verticalAlign: 'top', padding: '0.85rem', color: '#1e293b' }}>
                  <div style={{ fontWeight: 700, color: '#0f172a', marginBottom: '0.35rem' }}>
                    {step.title_ja || step.title}
                  </div>
                  <p style={{ margin: 0, lineHeight: 1.45, color: '#334155' }}>
                    {step.description_ja || '手順説明'}
                  </p>
                  {step.safety_warnings && step.safety_warnings.length > 0 && (
                    <div style={{ fontSize: '0.72rem', color: '#b91c1c', marginTop: '0.35rem' }}>
                      <strong>注意:</strong> {step.safety_warnings[0]}
                    </div>
                  )}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>

      {/* Footer Signatures */}
      <div
        style={{
          marginTop: '2rem',
          borderTop: '2px solid #0f172a',
          paddingTop: '1rem',
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: '0.75rem',
          color: '#475569',
        }}
      >
        <div>
          <div>Document Prepared By: <strong>Process Engineering AI Pipeline</strong></div>
          <div>Empirical Evidence: Multimodal video optical flow + speech analysis</div>
        </div>

        <div style={{ textAlign: 'right' }}>
          <div>Approved By: <strong>ET Engineering Team</strong></div>
          <div>Certification: ISO 9001:2015 Manufacturing Quality Compliance</div>
        </div>
      </div>
    </div>
  );
};
