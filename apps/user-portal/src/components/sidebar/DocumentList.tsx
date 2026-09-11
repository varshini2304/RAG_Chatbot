import React, { useState } from 'react';
import type { DocumentItem } from '../../types';

interface DocumentListProps {
  documents: DocumentItem[];
  selectedDoc: string | null;
  onSelectDoc: (filename: string) => void;
  onDeleteDoc: (filename: string) => void;
}

export const DocumentList: React.FC<DocumentListProps> = ({
  documents,
  selectedDoc,
  onSelectDoc,
  onDeleteDoc,
}) => {
  const [searchQuery, setSearchQuery] = useState('');

  const filteredDocs = documents.filter((doc) =>
    doc.source_file.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (documents.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '1rem', color: 'var(--text-secondary)', fontSize: '0.78rem' }}>
        <h3 style={{ fontSize: '0.88rem', fontWeight: 600, color: '#ffffff', marginBottom: '0.2rem' }}>
          No documents yet
        </h3>
        <p>Upload a PDF or TXT file to begin.</p>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      <input
        type="text"
        className="doc-search-input"
        placeholder="🔍 Search documents..."
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
      />

      {filteredDocs.length > 0 && (
        <select
          className="doc-select"
          value={selectedDoc || filteredDocs[0].source_file}
          onChange={(e) => onSelectDoc(e.target.value)}
        >
          {filteredDocs.map((doc) => (
            <option key={doc.source_file} value={doc.source_file}>
              {doc.source_file}
            </option>
          ))}
        </select>
      )}

      {filteredDocs.map((doc) => {
        const isPdf = doc.document_type.toLowerCase() === 'pdf';
        const badgeClass = isPdf ? 'sb-badge-pdf' : 'sb-badge-txt';
        const isActive = selectedDoc === doc.source_file;

        let statusIcon = '⏳';
        if (doc.embedding_status === 'completed') statusIcon = '✅';
        if (doc.embedding_status === 'failed') statusIcon = '⚠️';

        return (
          <div key={doc.source_file} className="doc-card-row">
            <div
              className={`sb-doc ${isActive ? 'sb-doc-active' : ''}`}
              onClick={() => onSelectDoc(doc.source_file)}
            >
              <div className={`sb-doc-badge ${badgeClass}`}>
                {doc.document_type.toUpperCase()}
              </div>
              <div className="sb-doc-info">
                <p className="sb-doc-name">{doc.source_file}</p>
                <p className="sb-doc-meta">
                  {doc.document_type.toUpperCase()} • {doc.chunk_count} chunks
                </p>
              </div>
              <div className="sb-doc-status">{statusIcon}</div>
            </div>
            <button
              type="button"
              className="sb-doc-del-btn"
              title={`Delete ${doc.source_file}`}
              onClick={(e) => {
                e.stopPropagation();
                onDeleteDoc(doc.source_file);
              }}
            >
              ⋮
            </button>
          </div>
        );
      })}
    </div>
  );
};
