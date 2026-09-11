import React, { useState } from 'react';
import type { SourceReference } from '../../types';

interface SourceReferencesProps {
  sources: SourceReference[];
}

export const SourceReferences: React.FC<SourceReferencesProps> = ({ sources }) => {
  const [expanded, setExpanded] = useState(false);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="sources-expander">
      <div
        className="sources-header"
        onClick={() => setExpanded(!expanded)}
      >
        <span>Source References ({sources.length})</span>
        <span>{expanded ? '▲' : '▼'}</span>
      </div>

      {expanded && (
        <div className="sources-grid">
          {sources.map((source, index) => {
            const isPdf = source.document_type.toLowerCase() === 'pdf';
            const badgeClass = isPdf ? 'sb-badge-pdf' : 'sb-badge-txt';

            return (
              <div key={source.chunk_id ? source.chunk_id : `source_${index}`} className="source-card">
                <div className="source-card-top">
                  <span className="source-rank">#{source.rank !== undefined ? source.rank : index + 1}</span>
                  <div className={`sb-doc-badge ${badgeClass}`}>
                    {source.document_type.toUpperCase()}
                  </div>
                </div>
                <span className="source-filename" title={source.source_file}>
                  {source.source_file}
                </span>
                <span className="source-page">Page {source.page_number}</span>
                <p className="source-preview">{source.content}</p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
