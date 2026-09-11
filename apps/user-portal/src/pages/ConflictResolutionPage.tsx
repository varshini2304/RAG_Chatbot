import React from 'react';
import { useSopWorkflow } from '../context/WorkflowContext';
import { ConflictCard } from '../components/conflicts/ConflictCard';

interface ConflictResolutionPageProps {
  onProceedToReview: () => void;
}

export const ConflictResolutionPage: React.FC<ConflictResolutionPageProps> = ({
  onProceedToReview,
}) => {
  const {
    conflicts,
    resolveConflict,
    seekTo,
    setCurrentStage,
    hasUnresolvedConflicts,
  } = useSopWorkflow();

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
            Phase 4: Conflict Detection & Conservative Resolution
          </h2>
          <span style={{ fontSize: '0.74rem', color: 'var(--sop-text-secondary)' }}>
            Empirical video evidence cross-referenced against authoritative reference documentation
          </span>
        </div>

        <button
          type="button"
          className="sop-btn sop-btn-primary"
          onClick={() => {
            setCurrentStage(5);
            onProceedToReview();
          }}
        >
          Proceed to Expert Review (Phase 5) →
        </button>
      </div>

      {/* Safety Notice */}
      <div className="sop-callout sop-callout-info">
        <div>
          <strong>Safety-Critical Conflict Policy:</strong> AI models must never silently choose between observed field
          actions and formal documentation specifications. When differences occur (e.g. tool selection, torque ratings, or PPE),
          a human process engineer must explicitly select a resolution and log a compliance rationale.
        </div>
      </div>

      {/* Conflicts List or Truthful Empty State */}
      {conflicts.length === 0 ? (
        <div className="sop-card" style={{ padding: '3rem', textAlign: 'center' }}>
          <div style={{ fontSize: '2rem', marginBottom: '0.5rem', color: 'var(--sop-teal)' }}>✓</div>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--sop-text-primary)', margin: '0 0 0.25rem 0' }}>
            No conflicts available for review.
          </h3>
          <p style={{ fontSize: '0.78rem', color: 'var(--sop-text-secondary)', margin: 0, maxWidth: '400px', marginInline: 'auto' }}>
            All observed work steps align with documented technical guidelines or no discrepancies were flagged by the comparison model.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {conflicts.map((conflict) => (
            <ConflictCard
              key={conflict.id}
              conflict={conflict}
              onResolve={resolveConflict}
              onSeek={seekTo}
            />
          ))}
        </div>
      )}

      {/* Action Footer */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
        <button
          type="button"
          className={`sop-btn ${hasUnresolvedConflicts ? 'sop-btn-secondary' : 'sop-btn-primary'}`}
          onClick={() => {
            setCurrentStage(5);
            onProceedToReview();
          }}
        >
          {hasUnresolvedConflicts ? 'Proceed with Unresolved Conflicts →' : 'All Conflicts Cleared — Go to Expert Review →'}
        </button>
      </div>
    </div>
  );
};
