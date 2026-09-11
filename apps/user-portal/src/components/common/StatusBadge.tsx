import React from 'react';
import type { StageStatus, StepReviewStatus } from '../../types/sop';

interface StatusBadgeProps {
  status: StageStatus | StepReviewStatus | 'verified' | 'conflict' | 'resolved' | 'active';
  label?: string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  label,
  size = 'md',
}) => {
  let badgeClass = 'sop-badge-gray';
  let defaultLabel = status.toUpperCase();
  let icon = '•';

  switch (status) {
    case 'completed':
    case 'approved':
    case 'verified':
    case 'resolved':
      badgeClass = 'sop-badge-teal';
      icon = '✓';
      defaultLabel = status === 'completed' ? 'Completed' : status === 'approved' ? 'Approved' : 'Verified';
      break;

    case 'pending':
    case 'needs_review':
      badgeClass = 'sop-badge-amber';
      icon = '⏳';
      defaultLabel = status === 'needs_review' ? 'Needs Review' : 'Pending';
      break;

    case 'processing':
    case 'active':
      badgeClass = 'sop-badge-blue';
      icon = '⟳';
      defaultLabel = status === 'processing' ? 'Processing' : 'Active';
      break;

    case 'conflict':
    case 'failed':
    case 'rejected':
      badgeClass = 'sop-badge-red';
      icon = '⚠';
      defaultLabel = status === 'conflict' ? 'Conflict Detected' : status === 'rejected' ? 'Rejected' : 'Failed';
      break;

    case 'skipped':
      badgeClass = 'sop-badge-gray';
      icon = '⊘';
      defaultLabel = 'Skipped';
      break;

    case 'unavailable':
      badgeClass = 'sop-badge-gray';
      icon = '—';
      defaultLabel = 'Unavailable';
      break;
  }

  return (
    <span
      className={`sop-badge ${badgeClass}`}
      style={{
        fontSize: size === 'sm' ? '0.68rem' : '0.74rem',
        padding: size === 'sm' ? '0.15rem 0.45rem' : '0.22rem 0.6rem',
      }}
    >
      <span style={{ fontSize: '0.9em', opacity: 0.85 }}>{icon}</span>
      <span>{label || defaultLabel}</span>
    </span>
  );
};
