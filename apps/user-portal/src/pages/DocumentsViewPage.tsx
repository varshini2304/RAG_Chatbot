import React, { useState } from 'react';
import type { DocumentItem, PipelineStatus } from '../types';
import { documentService } from '../services/documentService';
import { ApiError } from '../services/api';

interface DocumentsViewPageProps {
  documents: DocumentItem[];
  pipelineStatus: PipelineStatus;
  onRefreshWorkspace: () => Promise<void>;
  onNavigateToChat: () => void;
}

export const DocumentsViewPage: React.FC<DocumentsViewPageProps> = ({
  documents,
  pipelineStatus,
  onRefreshWorkspace,
  onNavigateToChat,
}) => {
  const [isUploading, setIsUploading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    setIsUploading(true);
    setErrorMsg(null);
    try {
      await documentService.uploadDocument(file);
      await onRefreshWorkspace();
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : 'Upload failed.';
      setErrorMsg(msg);
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (filename: string) => {
    if (!window.confirm(`Delete "${filename}" from workspace?`)) return;
    try {
      await documentService.deleteDocument(filename);
      await onRefreshWorkspace();
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : 'Delete failed.';
      alert(`Delete Error: ${msg}`);
    }
  };

  const handleClear = async () => {
    if (!window.confirm('Clear all documents and embeddings from workspace?')) return;
    try {
      await documentService.clearWorkspace();
      await onRefreshWorkspace();
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : 'Clear failed.';
      alert(`Error: ${msg}`);
    }
  };

  const totalChunks = documents.reduce((acc, d) => acc + Number(d.chunk_count), 0);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Top Banner */}
      <div
        className="sop-card"
        style={{
          padding: '1rem 1.25rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: 'var(--sop-bg-panel)',
        }}
      >
        <div>
          <h2 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--sop-text-primary)', margin: 0 }}>
            Workspace Reference Documents
          </h2>
          <span style={{ fontSize: '0.74rem', color: 'var(--sop-text-secondary)' }}>
            Authoritative technical manuals, engineering schematics, and standard operating procedures
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <label className="sop-btn sop-btn-primary" style={{ cursor: 'pointer' }}>
            <span>{isUploading ? 'Uploading...' : '+ Ingest New Document'}</span>
            <input
              type="file"
              accept=".pdf,.txt,.png,.jpg,.jpeg,.webp,.tiff,.bmp"
              onChange={handleUpload}
              disabled={isUploading}
              style={{ display: 'none' }}
            />
          </label>

          <button
            type="button"
            className="sop-btn sop-btn-secondary"
            onClick={onNavigateToChat}
          >
            Ask Questions in RAG Chat →
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="sop-callout sop-callout-danger">
          <div>{errorMsg}</div>
        </div>
      )}

      {/* Metrics & Pipeline Status */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
        <div className="sop-card" style={{ padding: '1rem' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--sop-text-muted)', textTransform: 'uppercase' }}>Ingested Documents</div>
          <div className="sop-mono" style={{ fontSize: '1.25rem', fontWeight: 800, color: '#93c5fd', marginTop: '4px' }}>
            {documents.length}
          </div>
        </div>

        <div className="sop-card" style={{ padding: '1rem' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--sop-text-muted)', textTransform: 'uppercase' }}>Indexed Chunks</div>
          <div className="sop-mono" style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--sop-teal)', marginTop: '4px' }}>
            {totalChunks}
          </div>
        </div>

        <div className="sop-card" style={{ padding: '1rem' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--sop-text-muted)', textTransform: 'uppercase' }}>Vector Index (ChromaDB)</div>
          <div style={{ fontSize: '0.85rem', fontWeight: 700, color: pipelineStatus.vector_store ? 'var(--sop-teal)' : 'var(--sop-amber)', marginTop: '6px' }}>
            {pipelineStatus.vector_store ? '✓ Active & Ready' : 'Pending'}
          </div>
        </div>

        <div className="sop-card" style={{ padding: '1rem' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--sop-text-muted)', textTransform: 'uppercase' }}>Embedding Pipeline</div>
          <div style={{ fontSize: '0.85rem', fontWeight: 700, color: pipelineStatus.embeddings ? 'var(--sop-teal)' : 'var(--sop-amber)', marginTop: '6px' }}>
            {pipelineStatus.embeddings ? '✓ Completed' : 'Pending'}
          </div>
        </div>
      </div>

      {/* Documents Table */}
      <div className="sop-card">
        <div className="sop-card-header">
          <div className="sop-card-title">
            <span>📚 Document Repository</span>
          </div>
          {documents.length > 0 && (
            <button
              type="button"
              className="sop-btn sop-btn-secondary"
              style={{ color: '#f87171', padding: '0.2rem 0.5rem', fontSize: '0.7rem' }}
              onClick={handleClear}
            >
              Clear Workspace
            </button>
          )}
        </div>

        {documents.length === 0 ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--sop-text-muted)', fontSize: '0.8rem' }}>
            No documents in workspace. Upload a PDF or manual to enable document-grounded RAG query answering.
          </div>
        ) : (
          <table className="sop-table">
            <thead>
              <tr>
                <th>Document File Name</th>
                <th style={{ width: '90px' }}>Type</th>
                <th style={{ width: '100px' }}>Chunks</th>
                <th style={{ width: '130px' }}>Index Status</th>
                <th style={{ width: '80px', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.source_file}>
                  <td style={{ fontWeight: 600, color: 'var(--sop-text-primary)' }}>
                    📄 {doc.source_file}
                  </td>
                  <td className="sop-mono" style={{ textTransform: 'uppercase', color: 'var(--sop-text-muted)' }}>
                    {doc.document_type}
                  </td>
                  <td className="sop-mono" style={{ color: '#93c5fd' }}>
                    {doc.chunk_count}
                  </td>
                  <td>
                    <span className={`sop-badge ${doc.embedding_status === 'completed' ? 'sop-badge-teal' : 'sop-badge-amber'}`}>
                      {doc.embedding_status}
                    </span>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <button
                      type="button"
                      className="sop-btn sop-btn-secondary"
                      style={{ padding: '0.2rem 0.45rem', fontSize: '0.7rem', color: '#f87171' }}
                      onClick={() => handleDelete(doc.source_file)}
                      title="Delete document"
                    >
                      Delete ✕
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
