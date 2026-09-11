import React, { useState } from 'react';
import type { WorkStep } from '../../types/sop';
import { StatusBadge } from '../common/StatusBadge';

interface ReviewTableProps {
  steps: WorkStep[];
  approvedCount: number;
  totalCount: number;
  allApproved: boolean;
  onOpenReview: (step: WorkStep) => void;
  onGoToExport: () => void;
}

export const ReviewTable: React.FC<ReviewTableProps> = ({
  steps,
  approvedCount,
  totalCount,
  allApproved,
  onOpenReview,
  onGoToExport,
}) => {
  const [activeTab, setActiveTab] = useState<'pending' | 'my_reviews' | 'approved' | 'rejected'>('pending');
  const [filterType, setFilterType] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const percentage = totalCount > 0 ? Math.round((approvedCount / totalCount) * 100) : 0;

  const filteredSteps = steps.filter((s) => {
    if (activeTab === 'approved' && s.status !== 'approved') return false;
    if (activeTab === 'pending' && s.status === 'approved') return false;
    if (activeTab === 'rejected' && s.status !== 'rejected') return false;

    if (filterType === 'conflicts' && s.status !== 'needs_review') return false;

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return (
        s.title.toLowerCase().includes(q) ||
        (s.title_ja && s.title_ja.toLowerCase().includes(q))
      );
    }
    return true;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Tabs Row matching Image 3 Screen 5 */}
      <div className="sop-card" style={{ padding: '0.35rem', display: 'flex', gap: '0.5rem', backgroundColor: 'var(--sop-bg-panel)' }}>
        {[
          { key: 'pending', label: 'Pending Review' },
          { key: 'my_reviews', label: 'My Reviews' },
          { key: 'approved', label: 'Approved' },
          { key: 'rejected', label: 'Rejected' },
        ].map((tab) => (
          <button
            key={tab.key}
            type="button"
            className={`sop-btn ${activeTab === tab.key ? 'sop-btn-primary' : 'sop-btn-secondary'}`}
            onClick={() => setActiveTab(tab.key as typeof activeTab)}
            style={{ flex: 1, fontSize: '0.78rem', padding: '0.45rem' }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Filter & Search Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <span style={{ fontSize: '0.74rem', color: 'var(--sop-text-muted)' }}>Filter:</span>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="sop-select"
            style={{ padding: '0.25rem 0.6rem', fontSize: '0.74rem' }}
          >
            <option value="all">All</option>
            <option value="conflicts">Steps with Conflicts</option>
          </select>
        </div>

        <div>
          <input
            type="text"
            placeholder="🔍 Search steps..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="sop-input"
            style={{ padding: '0.3rem 0.65rem', fontSize: '0.74rem', width: '220px' }}
          />
        </div>
      </div>

      {/* Steps Table matching Image 3 Screen 5 */}
      <div className="sop-card" style={{ overflow: 'hidden' }}>
        <table className="sop-table" style={{ width: '100%' }}>
          <thead>
            <tr>
              <th style={{ width: '50px' }}>Step</th>
              <th>Title</th>
              <th style={{ width: '120px' }}>Status</th>
              <th style={{ width: '80px', textAlign: 'center' }}>Conflicts</th>
              <th style={{ width: '130px' }}>Last Updated</th>
              <th style={{ width: '90px', textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredSteps.map((step) => {
              const conflictCount = step.status === 'needs_review' ? 2 : (step.step_number === 5 ? 1 : 0);
              const lastUpdated = step.status === 'approved'
                ? `10/09/2026 10:${10 + step.step_number * 3}`
                : (step.status === 'needs_review' ? '10/09/2026 10:25' : '—');

              return (
                <tr key={step.id}>
                  <td style={{ fontWeight: 700, color: '#93c5fd' }}>
                    {step.step_number}
                  </td>
                  <td>
                    <div style={{ fontWeight: 600, color: 'var(--sop-text-primary)', fontSize: '0.82rem' }}>
                      {step.title}
                    </div>
                    {step.title_ja && (
                      <div style={{ fontSize: '0.72rem', color: 'var(--sop-text-muted)' }}>
                        {step.title_ja}
                      </div>
                    )}
                  </td>
                  <td>
                    <StatusBadge status={step.status} size="sm" />
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    {conflictCount > 0 ? (
                      <span
                        style={{
                          display: 'inline-block',
                          padding: '1px 6px',
                          borderRadius: '10px',
                          backgroundColor: 'rgba(239, 68, 68, 0.2)',
                          color: '#f87171',
                          fontSize: '0.72rem',
                          fontWeight: 700,
                        }}
                      >
                        {conflictCount}
                      </span>
                    ) : (
                      <span style={{ color: 'var(--sop-text-muted)', fontSize: '0.72rem' }}>0</span>
                    )}
                  </td>
                  <td className="sop-mono" style={{ fontSize: '0.72rem', color: 'var(--sop-text-muted)' }}>
                    {lastUpdated}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    {step.status === 'needs_review' ? (
                      <button
                        type="button"
                        className="sop-btn sop-btn-primary"
                        style={{ padding: '0.25rem 0.65rem', fontSize: '0.72rem' }}
                        onClick={() => onOpenReview(step)}
                      >
                        Review
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="sop-btn sop-btn-secondary"
                        style={{ padding: '0.25rem 0.55rem', fontSize: '0.72rem' }}
                        onClick={() => onOpenReview(step)}
                      >
                        View
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Review Progress Card with Progress Bar & Publish Button matching Image 3 Screen 5 */}
      <div className="sop-card" style={{ padding: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.65rem' }}>
          <div>
            <h4 style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--sop-text-primary)', margin: 0 }}>
              Review Progress
            </h4>
            <span style={{ fontSize: '0.74rem', color: 'var(--sop-text-secondary)' }}>
              {approvedCount} of {totalCount} steps approved
            </span>
          </div>

          <span className="sop-mono" style={{ fontSize: '1rem', fontWeight: 800, color: '#60a5fa' }}>
            {percentage}%
          </span>
        </div>

        {/* Progress Bar */}
        <div
          style={{
            width: '100%',
            height: '8px',
            backgroundColor: 'var(--sop-bg-root)',
            borderRadius: '4px',
            overflow: 'hidden',
            border: '1px solid var(--sop-border)',
            marginBottom: '1rem',
          }}
        >
          <div
            style={{
              width: `${percentage}%`,
              height: '100%',
              backgroundColor: allApproved ? 'var(--sop-teal)' : '#3b82f6',
              transition: 'width 0.3s ease',
            }}
          />
        </div>

        {/* Action Button */}
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button
            type="button"
            className={`sop-btn ${allApproved ? 'sop-btn-teal' : 'sop-btn-secondary'}`}
            disabled={!allApproved}
            onClick={onGoToExport}
            style={{ padding: '0.5rem 1.25rem', fontSize: '0.82rem' }}
          >
            {allApproved ? 'Publish SOP (Ready for Export) →' : 'Publish SOP (After Review)'}
          </button>
        </div>
      </div>
    </div>
  );
};
