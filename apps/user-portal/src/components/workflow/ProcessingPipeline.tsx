import React from 'react';
import type { PipelineStageInfo } from '../../types/sop';

interface ProcessingPipelineProps {
  stages: PipelineStageInfo[];
}

export const ProcessingPipeline: React.FC<ProcessingPipelineProps> = ({ stages }) => {
  // Format elapsed or estimated time
  const formatTimePill = (stg: PipelineStageInfo) => {
    if (stg.status === 'completed') {
      const sec = Math.round(stg.elapsed_sec || 8);
      const m = Math.floor(sec / 60);
      const s = sec % 60;
      return `Completed 00:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    }
    if (stg.status === 'processing') {
      return 'Processing Est. 01:20';
    }
    if (stg.status === 'skipped') {
      return 'Skipped (No Audio)';
    }
    return 'Pending';
  };

  const stageSubtitles: Record<string, string> = {
    video_intake: 'Validate file',
    audio_extraction: 'Extract & standardize',
    speech_transcription: 'ASR (Speech to Text)',
    step_detection: 'Identify steps',
    translation: 'Generate bilingual SOP',
  };

  return (
    <div className="sop-card" style={{ padding: '1.25rem' }}>
      <div style={{ position: 'relative', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        {/* Horizontal Connector Line running behind circles */}
        <div
          style={{
            position: 'absolute',
            top: '20px',
            left: '30px',
            right: '30px',
            height: '2px',
            backgroundColor: 'var(--sop-border)',
            zIndex: 1,
          }}
        />

        {stages.map((stg, idx) => {
          const isCompleted = stg.status === 'completed';
          const isProcessing = stg.status === 'processing';
          const isPending = stg.status === 'pending';
          const isSkipped = stg.status === 'skipped';

          // Circle styling
          let circleBg = 'var(--sop-bg-panel)';
          let circleColor = 'var(--sop-text-muted)';
          let circleBorder = '2px solid var(--sop-border)';
          let circleContent: React.ReactNode = idx + 1;

          if (isCompleted) {
            circleBg = '#10b981';
            circleColor = '#ffffff';
            circleBorder = '2px solid #10b981';
            circleContent = '✓';
          } else if (isProcessing) {
            circleBg = '#3b82f6';
            circleColor = '#ffffff';
            circleBorder = '2px solid #3b82f6';
            circleContent = idx + 1;
          } else if (isSkipped) {
            circleBg = 'var(--sop-amber-bg)';
            circleColor = '#f59e0b';
            circleBorder = '2px solid #f59e0b';
            circleContent = '—';
          }

          // Pill badge styling
          let pillBg = 'var(--sop-bg-root)';
          let pillColor = 'var(--sop-text-muted)';
          let pillBorder = '1px solid var(--sop-border)';

          if (isCompleted) {
            pillBg = 'rgba(16, 185, 129, 0.12)';
            pillColor = '#10b981';
            pillBorder = '1px solid rgba(16, 185, 129, 0.3)';
          } else if (isProcessing) {
            pillBg = 'rgba(59, 130, 246, 0.12)';
            pillColor = '#60a5fa';
            pillBorder = '1px solid rgba(59, 130, 246, 0.3)';
          } else if (isSkipped) {
            pillBg = 'rgba(245, 158, 11, 0.12)';
            pillColor = '#f59e0b';
            pillBorder = '1px solid rgba(245, 158, 11, 0.3)';
          }

          return (
            <div
              key={stg.key}
              style={{
                position: 'relative',
                zIndex: 2,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                textAlign: 'center',
                flex: 1,
                padding: '0 0.5rem',
              }}
            >
              {/* Stepper Circle */}
              <div
                style={{
                  width: '40px',
                  height: '40px',
                  borderRadius: '50%',
                  backgroundColor: circleBg,
                  color: circleColor,
                  border: circleBorder,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '0.92rem',
                  fontWeight: 700,
                  marginBottom: '0.65rem',
                  boxShadow: isProcessing
                    ? '0 0 0 4px rgba(59, 130, 246, 0.25)'
                    : isCompleted
                    ? '0 0 0 2px rgba(16, 185, 129, 0.2)'
                    : 'none',
                  transition: 'all 0.2s ease',
                }}
              >
                {circleContent}
              </div>

              {/* Stage Title */}
              <div
                style={{
                  fontSize: '0.82rem',
                  fontWeight: 700,
                  color: isPending ? 'var(--sop-text-secondary)' : 'var(--sop-text-primary)',
                  marginBottom: '0.15rem',
                }}
              >
                {stg.label}
              </div>

              {/* Stage Subtitle */}
              <div
                style={{
                  fontSize: '0.7rem',
                  color: 'var(--sop-text-muted)',
                  marginBottom: '0.5rem',
                  minHeight: '1.1rem',
                }}
              >
                {stageSubtitles[stg.key] || stg.description}
              </div>

              {/* Status Pill Badge */}
              <div
                style={{
                  fontSize: '0.68rem',
                  fontWeight: 600,
                  padding: '3px 8px',
                  borderRadius: '12px',
                  backgroundColor: pillBg,
                  color: pillColor,
                  border: pillBorder,
                  whiteSpace: 'nowrap',
                }}
              >
                {formatTimePill(stg)}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
