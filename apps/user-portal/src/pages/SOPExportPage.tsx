import React, { useState } from 'react';
import { useSopWorkflow } from '../context/WorkflowContext';
import { SOPDocumentView } from '../components/sop/SOPDocumentView';
import { AuditTrailView } from '../components/sop/AuditTrailView';
import { sopApi } from '../services/sopApi';

export const SOPExportPage: React.FC = () => {
  const { document, steps } = useSopWorkflow();
  const [activeTab, setActiveTab] = useState<'preview' | 'export' | 'audit'>('preview');
  const [langView, setLangView] = useState<'bilingual' | 'en' | 'ja'>('bilingual');
  const [exportNotice, setExportNotice] = useState<string | null>(null);

  // Sync current steps into document
  const compiledDocument = {
    ...document,
    steps,
  };

  const handleExport = async (format: 'pdf' | 'docx') => {
    setExportNotice(`Preparing ${format.toUpperCase()} export file...`);
    const res = await sopApi.exportSop(document.id, format);
    setExportNotice(res.message);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Top Banner matching Image 3 Screen 6 */}
      <div
        className="sop-card"
        style={{
          padding: '1rem 1.25rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: 'rgba(16, 185, 129, 0.12)',
          border: '1px solid rgba(16, 185, 129, 0.35)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '50%',
              backgroundColor: '#10b981',
              color: '#fff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1rem',
              fontWeight: 700,
            }}
          >
            ✓
          </div>
          <div>
            <h2 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
              All steps reviewed and approved
            </h2>
            <span style={{ fontSize: '0.74rem', color: '#86efac' }}>
              Your SOP is ready for export.
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div
            style={{
              width: '28px',
              height: '28px',
              borderRadius: '50%',
              backgroundColor: '#3b82f6',
              color: '#fff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '0.7rem',
              fontWeight: 700,
            }}
          >
            ET
          </div>
          <div style={{ textAlign: 'right', fontSize: '0.72rem' }}>
            <div style={{ color: 'var(--sop-text-muted)' }}>Approved by:</div>
            <div style={{ color: 'var(--sop-text-primary)', fontWeight: 600 }}>
              Engineering Team 10/09/2026 14:32
            </div>
          </div>
        </div>
      </div>

      {/* Action Toolbar matching Image 3 Screen 6 */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        {/* Tabs: Preview | Export | Audit Trail */}
        <div className="sop-mode-toggle">
          <button
            type="button"
            className={`sop-mode-btn ${activeTab === 'preview' ? 'active' : ''}`}
            onClick={() => setActiveTab('preview')}
          >
            Preview
          </button>
          <button
            type="button"
            className={`sop-mode-btn ${activeTab === 'export' ? 'active' : ''}`}
            onClick={() => setActiveTab('export')}
          >
            Export
          </button>
          <button
            type="button"
            className={`sop-mode-btn ${activeTab === 'audit' ? 'active' : ''}`}
            onClick={() => setActiveTab('audit')}
          >
            Audit Trail
          </button>
        </div>

        {/* Language View & Download Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span style={{ fontSize: '0.74rem', color: 'var(--sop-text-muted)' }}>Language View:</span>
            <select
              value={langView}
              onChange={(e) => setLangView(e.target.value as 'bilingual' | 'en' | 'ja')}
              className="sop-select"
              style={{ padding: '0.3rem 0.65rem', fontSize: '0.74rem' }}
            >
              <option value="bilingual">Bilingual (Side by side)</option>
              <option value="en">English Only</option>
              <option value="ja">日本語 Only</option>
            </select>
          </div>

          <button
            type="button"
            className="sop-btn sop-btn-primary"
            onClick={() => handleExport('pdf')}
            style={{ padding: '0.4rem 0.85rem', fontSize: '0.76rem' }}
          >
            📥 Download PDF
          </button>

          <button
            type="button"
            className="sop-btn sop-btn-secondary"
            onClick={() => handleExport('docx')}
            style={{ padding: '0.4rem 0.85rem', fontSize: '0.76rem' }}
          >
            Download DOCX
          </button>
        </div>
      </div>

      {exportNotice && (
        <div className="sop-callout sop-callout-info">
          <div>{exportNotice}</div>
        </div>
      )}

      {/* Tab Contents */}
      {activeTab === 'preview' && (
        <SOPDocumentView document={compiledDocument} langView={langView} />
      )}

      {activeTab === 'export' && (
        <div className="sop-card" style={{ padding: '2rem' }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--sop-text-primary)', margin: '0 0 0.5rem 0' }}>
            Official Document Export Channels
          </h3>
          <p style={{ fontSize: '0.78rem', color: 'var(--sop-text-secondary)', margin: '0 0 1.5rem 0', maxWidth: '500px' }}>
            Download compliant manufacturing shop-floor standard operating procedures in printable PDF or editable DOCX formats.
          </p>

          <div style={{ display: 'flex', gap: '1rem' }}>
            <button
              type="button"
              className="sop-btn sop-btn-primary"
              onClick={() => handleExport('pdf')}
              style={{ padding: '0.65rem 1.25rem' }}
            >
              📄 Download PDF (Print-Ready)
            </button>

            <button
              type="button"
              className="sop-btn sop-btn-secondary"
              onClick={() => handleExport('docx')}
              style={{ padding: '0.65rem 1.25rem' }}
            >
              📝 Download DOCX (Office Template)
            </button>
          </div>
        </div>
      )}

      {activeTab === 'audit' && (
        <AuditTrailView auditTrail={document.audit_trail} />
      )}
    </div>
  );
};
