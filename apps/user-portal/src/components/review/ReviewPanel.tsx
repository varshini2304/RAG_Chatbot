import React, { useState } from 'react';
import type { WorkStep, StepReviewStatus } from '../../types/sop';

interface ReviewPanelProps {
  step: WorkStep;
  isOpen: boolean;
  onClose: () => void;
  onSaveReview: (stepId: string, status: StepReviewStatus, notes: string) => Promise<void>;
}

export const ReviewPanel: React.FC<ReviewPanelProps> = ({
  step,
  isOpen,
  onClose,
  onSaveReview,
}) => {
  const [selectedStatus, setSelectedStatus] = useState<StepReviewStatus>(step.status);
  const [notes, setNotes] = useState<string>(step.reviewer_notes || '');
  const [isSaving, setIsSaving] = useState<boolean>(false);

  if (!isOpen) return null;

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await onSaveReview(step.id, selectedStatus, notes);
      onClose();
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(5, 7, 13, 0.8)',
        backdropFilter: 'blur(3px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 50,
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '540px',
          backgroundColor: 'var(--sop-bg-surface)',
          border: '1px solid var(--sop-border)',
          borderRadius: '8px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
          overflow: 'hidden',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            padding: '1rem 1.25rem',
            backgroundColor: 'var(--sop-bg-panel)',
            borderBottom: '1px solid var(--sop-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div>
            <h3 style={{ fontSize: '0.92rem', fontWeight: 700, color: 'var(--sop-text-primary)', margin: 0 }}>
              Expert Review: Step {step.step_number}
            </h3>
            <span style={{ fontSize: '0.74rem', color: 'var(--sop-text-secondary)' }}>
              {step.title}
            </span>
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{ color: 'var(--sop-text-muted)', fontSize: '1.2rem', cursor: 'pointer' }}
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.76rem', fontWeight: 600, color: 'var(--sop-text-secondary)', marginBottom: '0.4rem' }}>
              Validation Decision
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem' }}>
              <button
                type="button"
                className="sop-btn"
                style={{
                  backgroundColor: selectedStatus === 'approved' ? 'var(--sop-teal-bg)' : 'var(--sop-bg-elevated)',
                  borderColor: selectedStatus === 'approved' ? 'var(--sop-teal-border)' : 'var(--sop-border)',
                  color: selectedStatus === 'approved' ? 'var(--sop-teal)' : 'var(--sop-text-secondary)',
                }}
                onClick={() => setSelectedStatus('approved')}
              >
                ✓ Approve
              </button>

              <button
                type="button"
                className="sop-btn"
                style={{
                  backgroundColor: selectedStatus === 'needs_review' ? 'var(--sop-amber-bg)' : 'var(--sop-bg-elevated)',
                  borderColor: selectedStatus === 'needs_review' ? 'var(--sop-amber-border)' : 'var(--sop-border)',
                  color: selectedStatus === 'needs_review' ? 'var(--sop-amber)' : 'var(--sop-text-secondary)',
                }}
                onClick={() => setSelectedStatus('needs_review')}
              >
                ⏳ Request Changes
              </button>

              <button
                type="button"
                className="sop-btn"
                style={{
                  backgroundColor: selectedStatus === 'rejected' ? 'var(--sop-red-bg)' : 'var(--sop-bg-elevated)',
                  borderColor: selectedStatus === 'rejected' ? 'var(--sop-red-border)' : 'var(--sop-border)',
                  color: selectedStatus === 'rejected' ? 'var(--sop-red)' : 'var(--sop-text-secondary)',
                }}
                onClick={() => setSelectedStatus('rejected')}
              >
                ✕ Reject
              </button>
            </div>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.76rem', fontWeight: 600, color: 'var(--sop-text-secondary)', marginBottom: '0.4rem' }}>
              Auditor / Quality Comments
            </label>
            <textarea
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Document reasons for approval, changes requested, or compliance observations..."
              style={{
                width: '100%',
                padding: '0.65rem 0.85rem',
                borderRadius: '6px',
                backgroundColor: 'var(--sop-bg-root)',
                border: '1px solid var(--sop-border)',
                color: 'var(--sop-text-primary)',
                fontSize: '0.78rem',
                resize: 'vertical',
              }}
            />
          </div>
        </div>

        {/* Footer */}
        <div
          style={{
            padding: '0.85rem 1.25rem',
            backgroundColor: 'var(--sop-bg-panel)',
            borderTop: '1px solid var(--sop-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-end',
            gap: '0.65rem',
          }}
        >
          <button
            type="button"
            className="sop-btn sop-btn-secondary"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            type="button"
            className="sop-btn sop-btn-primary"
            disabled={isSaving}
            onClick={handleSave}
          >
            {isSaving ? 'Saving Audit Record...' : 'Confirm Review Sign-off'}
          </button>
        </div>
      </div>
    </div>
  );
};
