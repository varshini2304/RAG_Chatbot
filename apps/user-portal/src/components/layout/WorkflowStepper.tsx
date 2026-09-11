import React from 'react';
import type { WorkflowStageNumber } from '../../types/sop';

interface WorkflowStepperProps {
  currentStage: WorkflowStageNumber;
  onSelectStage: (stage: WorkflowStageNumber) => void;
  hasConflicts: boolean;
  allApproved: boolean;
}

export const WorkflowStepper: React.FC<WorkflowStepperProps> = ({
  currentStage,
  onSelectStage,
  hasConflicts,
  allApproved,
}) => {
  const stages: { number: WorkflowStageNumber; label: string; locked?: boolean }[] = [
    { number: 1, label: 'Video Ingestion' },
    { number: 2, label: 'Step Timeline' },
    { number: 3, label: 'Structured Detail' },
    { number: 4, label: hasConflicts ? 'Conflicts (1 Alert)' : 'Conflict Resolution' },
    { number: 5, label: 'Expert Review' },
    { number: 6, label: allApproved ? 'Bilingual SOP' : 'Bilingual SOP (Locked)', locked: !allApproved },
  ];

  return (
    <nav aria-label="Workflow progress" className="sop-stepper-bar">
      {stages.map((stg, idx) => {
        const isCurrent = currentStage === stg.number;
        const isCompleted = currentStage > stg.number;
        const isLocked = stg.locked && !isCurrent;
        const isConflictAlert = stg.number === 4 && hasConflicts;

        let nodeClass = '';
        if (isCurrent) nodeClass = 'active';
        else if (isCompleted) nodeClass = 'completed';
        else if (isConflictAlert) nodeClass = 'needs-review';
        else if (isLocked) nodeClass = 'locked';

        return (
          <React.Fragment key={stg.number}>
            <button
              type="button"
              className={`sop-step-node ${nodeClass}`}
              onClick={() => {
                if (!isLocked) onSelectStage(stg.number);
              }}
              disabled={isLocked}
              title={isLocked ? 'Export is locked until all steps are approved in Expert Review' : `Navigate to ${stg.label}`}
            >
              <span className="sop-step-num">
                {isCompleted ? '✓' : isLocked ? '🔒' : stg.number}
              </span>
              <span>{stg.label}</span>
            </button>

            {idx < stages.length - 1 && (
              <span className="sop-step-separator" aria-hidden="true">
                →
              </span>
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
};
