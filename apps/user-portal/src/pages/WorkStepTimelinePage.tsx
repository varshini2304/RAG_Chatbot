import React, { useState } from 'react';
import { useSopWorkflow } from '../context/WorkflowContext';
import { VideoPlayer } from '../components/video/VideoPlayer';
import { WorkStepCard } from '../components/timeline/WorkStepCard';
import { WorkStepTable } from '../components/timeline/WorkStepTable';

interface WorkStepTimelinePageProps {
  onInspectStep: (stepId: string) => void;
}

export const WorkStepTimelinePage: React.FC<WorkStepTimelinePageProps> = ({ onInspectStep }) => {
  const {
    video,
    videoStreamUrl,
    steps,
    selectedStepId,
    setSelectedStepId,
    videoCurrentTime,
    setVideoCurrentTime,
    isPlaying,
    setIsPlaying,
    playbackRate,
    setPlaybackRate,
    seekTo,
    setCurrentStage,
  } = useSopWorkflow();

  const [viewMode, setViewMode] = useState<'timeline' | 'table' | 'transcript'>('timeline');
  const [rightPanelTab, setRightPanelTab] = useState<'transcript' | 'waveform'>('transcript');
  const [stepFilter, setStepFilter] = useState<'all' | 'verified' | 'needs_review'>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const currentStep = steps.find((s) => s.id === selectedStepId) || steps[0];
  const isSilent = video.audio_codec === null;

  // Japanese dialogue transcript segments matching reference Image 3
  const transcriptSegments = [
    { timeSec: 0, timeStr: '00:05', speaker: 'Operator', text: 'それでは、本日の機械保守点検作業を開始します。' },
    { timeSec: 25, timeStr: '00:25', speaker: 'Operator', text: '保護手袋と保護めがねの着用を確認します。' },
    { timeSec: 80, timeStr: '01:20', speaker: 'Operator', text: 'それでは、主電源を切ります。' },
    { timeSec: 95, timeStr: '01:35', speaker: 'Operator', text: '次に、操作盤のメインスイッチに手を近づけます。' },
    { timeSec: 105, timeStr: '01:45', speaker: 'Operator', text: 'メインスイッチをOFFの位置に確実に切り替えます。' },
    { timeSec: 130, timeStr: '02:10', speaker: 'Operator', text: 'インジケーターランプが消灯していることを確認します。' },
    { timeSec: 155, timeStr: '02:35', speaker: 'Operator', text: '続いて、安全カバーの取り外し作業に移ります。' },
    { timeSec: 165, timeStr: '02:45', speaker: 'Operator', text: '前部のネジを2本緩めてカバーを取り外します。' },
    { timeSec: 190, timeStr: '03:10', speaker: 'Operator', text: '内部プーリーおよびタイミングベルトの摩耗状態を点検します。' },
    { timeSec: 260, timeStr: '04:20', speaker: 'Operator', text: '作業エリア内の切削屑と異物を清掃します。' },
  ];

  // Filtering steps
  const filteredSteps = steps.filter((s) => {
    if (stepFilter === 'verified' && s.status !== 'approved') return false;
    if (stepFilter === 'needs_review' && s.status !== 'needs_review') return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchTitle = s.title.toLowerCase().includes(q);
      const matchTitleJa = s.title_ja?.toLowerCase().includes(q);
      const matchDesc = s.description.toLowerCase().includes(q);
      return matchTitle || matchTitleJa || matchDesc;
    }
    return true;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Top Header matching Image 3 Screen 2 */}
      <div
        className="sop-card"
        style={{
          padding: '0.85rem 1.25rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: 'var(--sop-bg-panel)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--sop-text-primary)' }}>
              2. Work-Step Timeline & Keyframe Review
            </span>
            <span className="sop-mono" style={{ fontSize: '0.75rem', color: '#93c5fd', backgroundColor: 'var(--sop-bg-root)', padding: '2px 6px', borderRadius: '4px', border: '1px solid var(--sop-border)' }}>
              {video.filename}
            </span>
            <span className="sop-badge sop-badge-teal">Processed</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', borderLeft: '1px solid var(--sop-border)', paddingLeft: '1rem' }}>
            <span style={{ fontSize: '0.74rem', color: 'var(--sop-text-muted)' }}>
              Total Steps: <strong style={{ color: 'var(--sop-text-primary)' }}>{steps.length}</strong>
            </span>
            <span style={{ fontSize: '0.74rem', color: 'var(--sop-text-muted)' }}>
              Duration: <strong style={{ color: 'var(--sop-text-primary)' }}>09:05</strong>
            </span>
            <span style={{ fontSize: '0.74rem', color: 'var(--sop-text-muted)' }}>
              Language: <strong style={{ color: 'var(--sop-text-primary)' }}>ja (0.98)</strong>
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {/* View Mode Toggle: Timeline View | Table View | Transcript View */}
          <div className="sop-mode-toggle">
            <button
              type="button"
              className={`sop-mode-btn ${viewMode === 'timeline' ? 'active' : ''}`}
              onClick={() => setViewMode('timeline')}
            >
              Timeline View
            </button>
            <button
              type="button"
              className={`sop-mode-btn ${viewMode === 'table' ? 'active' : ''}`}
              onClick={() => setViewMode('table')}
            >
              Table View
            </button>
            <button
              type="button"
              className={`sop-mode-btn ${viewMode === 'transcript' ? 'active' : ''}`}
              onClick={() => setViewMode('transcript')}
            >
              Transcript View
            </button>
          </div>

          <button
            type="button"
            className="sop-btn sop-btn-primary"
            onClick={() => {
              setCurrentStage(3);
              onInspectStep(currentStep?.id || steps[0]?.id);
            }}
            style={{ padding: '0.4rem 0.85rem', fontSize: '0.78rem' }}
          >
            Inspect Step Detail (Phase 3) →
          </button>
        </div>
      </div>

      {/* Main Upper Grid: Left Video Player + Right Transcript / Waveform */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: '1.25rem' }}>
        {/* Left: Video Player */}
        <div>
          <VideoPlayer
            video={video}
            streamUrl={videoStreamUrl}
            currentTime={videoCurrentTime}
            isPlaying={isPlaying}
            playbackRate={playbackRate}
            steps={steps}
            currentStep={currentStep}
            onTimeUpdate={setVideoCurrentTime}
            onPlayPause={() => setIsPlaying(!isPlaying)}
            onRateChange={setPlaybackRate}
            onStepClick={(id, startTime) => {
              setSelectedStepId(id);
              seekTo(startTime);
            }}
          />
        </div>

        {/* Right: Tabbed Panel [Transcript] and [Audio Waveform] matching Image 3 Screen 2 */}
        <div className="sop-card" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          {/* Tabs */}
          <div style={{ display: 'flex', borderBottom: '1px solid var(--sop-border)', backgroundColor: 'var(--sop-bg-panel)' }}>
            <button
              type="button"
              onClick={() => setRightPanelTab('transcript')}
              style={{
                flex: 1,
                padding: '0.65rem',
                fontSize: '0.78rem',
                fontWeight: 600,
                border: 'none',
                backgroundColor: rightPanelTab === 'transcript' ? 'var(--sop-bg-surface)' : 'transparent',
                color: rightPanelTab === 'transcript' ? '#60a5fa' : 'var(--sop-text-muted)',
                borderBottom: rightPanelTab === 'transcript' ? '2px solid #3b82f6' : '2px solid transparent',
                cursor: 'pointer',
              }}
            >
              Transcript
            </button>
            <button
              type="button"
              onClick={() => setRightPanelTab('waveform')}
              style={{
                flex: 1,
                padding: '0.65rem',
                fontSize: '0.78rem',
                fontWeight: 600,
                border: 'none',
                backgroundColor: rightPanelTab === 'waveform' ? 'var(--sop-bg-surface)' : 'transparent',
                color: rightPanelTab === 'waveform' ? '#60a5fa' : 'var(--sop-text-muted)',
                borderBottom: rightPanelTab === 'waveform' ? '2px solid #3b82f6' : '2px solid transparent',
                cursor: 'pointer',
              }}
            >
              Audio Waveform
            </button>
          </div>

          {/* Tab 1: Spoken Dialogue Transcript */}
          {rightPanelTab === 'transcript' && (
            <div style={{ flex: 1, padding: '0.75rem', overflowY: 'auto', maxHeight: '380px', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {isSilent ? (
                <div className="sop-callout sop-callout-warning">
                  <div>
                    <strong>No Audio Stream:</strong> This demonstration has no audio track. Visual optical flow is the primary evidence grounding.
                  </div>
                </div>
              ) : (
                transcriptSegments.map((seg, idx) => {
                  const isActive = videoCurrentTime >= seg.timeSec && (idx === transcriptSegments.length - 1 || videoCurrentTime < transcriptSegments[idx + 1].timeSec);

                  return (
                    <div
                      key={idx}
                      onClick={() => seekTo(seg.timeSec)}
                      style={{
                        padding: '0.5rem 0.65rem',
                        borderRadius: '6px',
                        backgroundColor: isActive ? 'var(--sop-bg-hover)' : 'transparent',
                        border: '1px solid',
                        borderColor: isActive ? 'var(--sop-border-focus)' : 'transparent',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.2rem' }}>
                        <span className="sop-mono" style={{ fontSize: '0.72rem', color: isActive ? '#60a5fa' : 'var(--sop-text-muted)', fontWeight: 600 }}>
                          {seg.timeStr}
                        </span>
                        <span style={{ fontSize: '0.68rem', color: 'var(--sop-text-muted)' }}>
                          {seg.speaker}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.78rem', color: isActive ? '#f8fafc' : 'var(--sop-text-secondary)', lineHeight: 1.4 }}>
                        {seg.text}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          )}

          {/* Tab 2: Audio Waveform Visualizer */}
          {rightPanelTab === 'waveform' && (
            <div style={{ flex: 1, padding: '1rem', display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--sop-text-muted)' }}>
                <span>Standardized 16 kHz Mono PCM</span>
                <span className="sop-mono">EBU R128 (-23 LUFS)</span>
              </div>

              {/* Graphical Waveform Bars */}
              <div
                style={{
                  height: '110px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '2px',
                  padding: '0.5rem',
                  backgroundColor: 'var(--sop-bg-root)',
                  borderRadius: '6px',
                  border: '1px solid var(--sop-border)',
                }}
              >
                {Array.from({ length: 48 }).map((_, i) => {
                  const normalizedTime = (videoCurrentTime / (video.duration_sec || 1)) * 48;
                  const isPast = i <= normalizedTime;
                  // Dynamic amplitude profile
                  const heightPct = Math.max(12, Math.sin(i * 0.45) * 45 + Math.cos(i * 0.25) * 35 + 20);

                  return (
                    <div
                      key={i}
                      onClick={() => seekTo((i / 48) * video.duration_sec)}
                      style={{
                        flex: 1,
                        height: `${heightPct}%`,
                        backgroundColor: isPast ? '#3b82f6' : '#334155',
                        borderRadius: '2px',
                        cursor: 'pointer',
                        transition: 'background-color 0.1s ease',
                      }}
                    />
                  );
                })}
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--sop-text-muted)' }}>
                <span>00:00</span>
                <span className="sop-mono">Timecode: {Math.floor(videoCurrentTime)}s</span>
                <span>09:05</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Bottom Section: Detected Work Steps (12) matching Image 3 Screen 2 */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <h3 style={{ fontSize: '0.92rem', fontWeight: 700, color: 'var(--sop-text-primary)', margin: 0 }}>
              Detected Work Steps ({steps.length})
            </h3>

            {/* Filter */}
            <select
              value={stepFilter}
              onChange={(e) => setStepFilter(e.target.value as 'all' | 'verified' | 'needs_review')}
              className="sop-select"
              style={{ padding: '0.25rem 0.6rem', fontSize: '0.74rem' }}
            >
              <option value="all">All Steps</option>
              <option value="verified">Verified Only</option>
              <option value="needs_review">Needs Review</option>
            </select>
          </div>

          {/* Search */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <input
              type="text"
              placeholder="🔍 Search steps..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="sop-input"
              style={{ padding: '0.3rem 0.65rem', fontSize: '0.74rem', width: '200px' }}
            />
          </div>
        </div>

        {/* View Mode 1: Timeline Card Strip */}
        {viewMode === 'timeline' && (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
              gap: '1rem',
            }}
          >
            {filteredSteps.map((step) => (
              <WorkStepCard
                key={step.id}
                step={step}
                isSelected={step.id === selectedStepId}
                onSelect={(id) => {
                  setSelectedStepId(id);
                  seekTo(step.start_time);
                }}
                onSeek={seekTo}
              />
            ))}
          </div>
        )}

        {/* View Mode 2: Table View */}
        {viewMode === 'table' && (
          <WorkStepTable
            steps={filteredSteps}
            selectedStepId={selectedStepId}
            onSelect={(id) => {
              setSelectedStepId(id);
              const found = steps.find((s) => s.id === id);
              if (found) seekTo(found.start_time);
            }}
            onSeek={seekTo}
          />
        )}

        {/* View Mode 3: Full Transcript View */}
        {viewMode === 'transcript' && (
          <div className="sop-card" style={{ padding: '1rem' }}>
            <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--sop-text-primary)', margin: '0 0 0.75rem 0' }}>
              Full Japanese Speech-to-Text Transcript (Faster-Whisper base)
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
              {transcriptSegments.map((seg, idx) => (
                <div
                  key={idx}
                  onClick={() => seekTo(seg.timeSec)}
                  style={{
                    display: 'flex',
                    alignItems: 'baseline',
                    gap: '1rem',
                    padding: '0.5rem 0.75rem',
                    borderRadius: '4px',
                    backgroundColor: 'var(--sop-bg-panel)',
                    cursor: 'pointer',
                  }}
                >
                  <span className="sop-mono" style={{ fontSize: '0.74rem', color: '#60a5fa', flexShrink: 0 }}>
                    {seg.timeStr}
                  </span>
                  <span style={{ fontSize: '0.8rem', color: 'var(--sop-text-primary)' }}>
                    {seg.text}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
