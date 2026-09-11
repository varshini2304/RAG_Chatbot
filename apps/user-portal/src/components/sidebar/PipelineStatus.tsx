import React from 'react';
import type { PipelineStatus as PipelineStatusType } from '../../types';

interface PipelineStatusProps {
  status: PipelineStatusType;
}

export const PipelineStatus: React.FC<PipelineStatusProps> = ({ status }) => {
  const steps = [
    { label: 'Text Extraction', done: status.text_extraction },
    { label: 'Chunking', done: status.chunking },
    { label: 'Embeddings', done: status.embeddings },
    { label: 'Vector Store', done: status.vector_store },
  ];

  return (
    <div className="sb-pipeline">
      {steps.map((step) => {
        const iconCls = step.done ? 'sb-pipe-done' : 'sb-pipe-wait';
        const statusCls = step.done ? 'sb-pipe-status-done' : 'sb-pipe-status-wait';
        const statusText = step.done ? 'Completed' : 'Pending';
        const icon = step.done ? '✓' : '○';

        return (
          <div key={step.label} className="sb-pipe-step">
            <span className={`sb-pipe-icon ${iconCls}`}>{icon}</span>
            <span className="sb-pipe-name">{step.label}</span>
            <span className={`sb-pipe-status ${statusCls}`}>{statusText}</span>
          </div>
        );
      })}
    </div>
  );
};
