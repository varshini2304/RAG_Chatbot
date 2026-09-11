import React, { useState } from 'react';
import { useSopWorkflow } from '../context/WorkflowContext';
import { ReviewTable } from '../components/review/ReviewTable';
import { ReviewPanel } from '../components/review/ReviewPanel';
import type { WorkStep, StepReviewStatus } from '../types/sop';

interface ExpertReviewPageProps {
  onGoToExport: () => void;
}

export const ExpertReviewPage: React.FC<ExpertReviewPageProps> = ({ onGoToExport }) => {
  const {
    steps,
    approvedCount,
    totalStepsCount,
    allStepsApproved,
    updateStepReview,
    setCurrentStage,
  } = useSopWorkflow();

  const [reviewingStep, setReviewingStep] = useState<WorkStep | null>(null);

  const handleOpenReview = (step: WorkStep) => {
    setReviewingStep(step);
  };

  const handleCloseReview = () => {
    setReviewingStep(null);
  };

  const handleSaveReview = async (stepId: string, status: StepReviewStatus, notes: string) => {
    await updateStepReview(stepId, status, notes);
  };

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
            Phase 5: Expert Review & Human Approval Gate
          </h2>
          <span style={{ fontSize: '0.74rem', color: 'var(--sop-text-secondary)' }}>
            Mandatory quality validation gate before standard operating procedure publication
          </span>
        </div>

        <button
          type="button"
          className={`sop-btn ${allStepsApproved ? 'sop-btn-teal' : 'sop-btn-secondary'}`}
          disabled={!allStepsApproved}
          onClick={() => {
            if (allStepsApproved) {
              setCurrentStage(6);
              onGoToExport();
            }
          }}
          title={allStepsApproved ? 'Navigate to final bilingual SOP export' : 'All steps must be approved before export'}
        >
          {allStepsApproved ? 'Proceed to Final Bilingual SOP (Phase 6) →' : 'Export Gate Locked 🔒'}
        </button>
      </div>

      {/* Review Table & Progress */}
      <ReviewTable
        steps={steps}
        approvedCount={approvedCount}
        totalCount={totalStepsCount}
        allApproved={allStepsApproved}
        onOpenReview={handleOpenReview}
        onGoToExport={() => {
          setCurrentStage(6);
          onGoToExport();
        }}
      />

      {/* Review Modal Dialog */}
      {reviewingStep && (
        <ReviewPanel
          step={reviewingStep}
          isOpen={true}
          onClose={handleCloseReview}
          onSaveReview={handleSaveReview}
        />
      )}
    </div>
  );
};
