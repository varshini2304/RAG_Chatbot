import React, { useState } from 'react';
import { useSopWorkflow } from '../context/WorkflowContext';

interface WorkStepDetailPageProps {
  onBackToTimeline: () => void;
  onProceedToConflicts: () => void;
}

export const WorkStepDetailPage: React.FC<WorkStepDetailPageProps> = ({
  onBackToTimeline,
  onProceedToConflicts,
}) => {
  const {
    steps,
    selectedStepId,
    setSelectedStepId,
    seekTo,
    setCurrentStage,
  } = useSopWorkflow();

  const [activeTab, setActiveTab] = useState<'overview' | 'transcript' | 'evidence' | 'docs' | 'comments'>('overview');
  const [copiedLang, setCopiedLang] = useState<'en' | 'ja' | null>(null);

  const currentIndex = steps.findIndex((s) => s.id === selectedStepId);
  const stepIndex = currentIndex >= 0 ? currentIndex : 2; // Default to step 3 matching Image 2
  const currentStep = steps[stepIndex] || steps[0];

  const hasPrev = stepIndex > 0;
  const hasNext = stepIndex < steps.length - 1;

  const handlePrev = () => {
    if (hasPrev) {
      const prevStep = steps[stepIndex - 1];
      setSelectedStepId(prevStep.id);
      seekTo(prevStep.start_time);
    }
  };

  const handleNext = () => {
    if (hasNext) {
      const nextStep = steps[stepIndex + 1];
      setSelectedStepId(nextStep.id);
      seekTo(nextStep.start_time);
    }
  };

  const formatTime = (seconds: number): string => {
    const totalSec = Math.max(0, Math.floor(seconds));
    const h = Math.floor(totalSec / 3600);
    const m = Math.floor((totalSec % 3600) / 60);
    const s = totalSec % 60;
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const formatDuration = (seconds: number): string => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const copyToClipboard = (text: string, lang: 'en' | 'ja') => {
    void navigator.clipboard.writeText(text);
    setCopiedLang(lang);
    setTimeout(() => setCopiedLang(null), 2000);
  };

  // Specific evidence items for Step 3 matching Image 2
  const step3Evidence = [
    { time: '01:20', timeSec: 80, en: 'Locate main switch', ja: '主電源スイッチを確認' },
    { time: '01:35', timeSec: 95, en: 'Hand approaches switch', ja: '手をスイッチに近づける' },
    { time: '01:45', timeSec: 105, en: 'Turn switch to OFF', ja: 'スイッチをOFFにする' },
    { time: '02:10', timeSec: 130, en: 'Indicator lamp turns off', ja: 'インジケーターランプが消灯' },
  ];

  // Specific English and Japanese instructions for Step 3 matching Image 2
  const englishInstructions = [
    '1. Locate the main switch on the control panel.',
    '2. Ensure the machine is in idle state.',
    '3. Turn the main switch to the OFF position.',
    '4. Confirm that the indicator lamp is off.',
  ];

  const japaneseInstructions = [
    '1. 操作パネルにある主電源スイッチを確認します。',
    '2. 機械が停止状態であることを確認します。',
    '3. 主電源スイッチをOFFの位置に切り替えます。',
    '4. インジケーターランプが消灯していることを確認します。',
  ];

  const durationSec = (currentStep.end_time || 155) - (currentStep.start_time || 80);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Top Header Bar */}
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
        <button
          type="button"
          className="sop-btn sop-btn-secondary"
          onClick={onBackToTimeline}
          style={{ padding: '0.4rem 0.85rem', fontSize: '0.78rem' }}
        >
          ← Back to Timeline
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--sop-text-secondary)' }}>
            Step {stepIndex + 1} of {steps.length}
          </span>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <button
              type="button"
              className="sop-btn sop-btn-secondary"
              disabled={!hasPrev}
              onClick={handlePrev}
              style={{ padding: '0.35rem 0.65rem', fontSize: '0.72rem' }}
            >
              &lt;
            </button>
            <button
              type="button"
              className="sop-btn sop-btn-secondary"
              disabled={!hasNext}
              onClick={handleNext}
              style={{ padding: '0.35rem 0.65rem', fontSize: '0.72rem' }}
            >
              &gt;
            </button>
          </div>

          <button
            type="button"
            className="sop-btn sop-btn-primary"
            onClick={() => {
              setCurrentStage(4);
              onProceedToConflicts();
            }}
            style={{ padding: '0.4rem 0.85rem', fontSize: '0.78rem', marginLeft: '0.5rem' }}
          >
            Proceed to Conflicts (Phase 4) →
          </button>
        </div>
      </div>

      {/* Step Header Banner matching Image 2 Screen 3 */}
      <div
        className="sop-card"
        style={{
          padding: '1.25rem',
          display: 'grid',
          gridTemplateColumns: '260px 1fr 220px',
          gap: '1.5rem',
          alignItems: 'center',
          backgroundColor: 'var(--sop-bg-panel)',
        }}
      >
        {/* Left: Keyframe Image Thumbnail with Time Overlay */}
        <div
          style={{
            position: 'relative',
            width: '100%',
            height: '145px',
            borderRadius: '6px',
            overflow: 'hidden',
            backgroundColor: '#000',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: '1px solid var(--sop-border)',
          }}
        >
          {/* Machine image visual simulation */}
          <div
            style={{
              width: '100%',
              height: '100%',
              background: 'radial-gradient(circle at 60% 40%, #dc2626 12%, #991b1b 18%, #334155 45%, #0f172a 90%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <div
              style={{
                width: '40px',
                height: '40px',
                borderRadius: '50%',
                backgroundColor: '#ef4444',
                border: '3px solid #fecaca',
                boxShadow: '0 0 15px rgba(239, 68, 68, 0.6)',
              }}
            />
          </div>

          <div
            style={{
              position: 'absolute',
              bottom: '8px',
              left: '8px',
              padding: '3px 8px',
              borderRadius: '4px',
              backgroundColor: 'rgba(0, 0, 0, 0.85)',
              color: '#fff',
              fontSize: '0.72rem',
              fontWeight: 600,
              fontFamily: 'var(--sop-font-mono)',
            }}
          >
            01:20 – 02:35
          </div>
        </div>

        {/* Center: Titles & Descriptions */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
          <div>
            <span className="sop-badge sop-badge-teal" style={{ marginBottom: '0.45rem', display: 'inline-block' }}>
              ✓ Verified
            </span>
          </div>

          <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--sop-text-primary)', margin: 0 }}>
            {currentStep.title}
          </h2>
          {currentStep.title_ja && (
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--sop-text-secondary)', margin: 0 }}>
              {currentStep.title_ja}
            </h3>
          )}

          <p style={{ fontSize: '0.8rem', color: 'var(--sop-text-secondary)', margin: '0.35rem 0 0 0' }}>
            {currentStep.description}
          </p>
          {currentStep.description_ja && (
            <p style={{ fontSize: '0.78rem', color: 'var(--sop-text-muted)', margin: 0 }}>
              {currentStep.description_ja}
            </p>
          )}
        </div>

        {/* Right: Technical Metadata Panel */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '0.5rem',
            padding: '0.85rem 1rem',
            backgroundColor: 'var(--sop-bg-root)',
            borderRadius: '6px',
            border: '1px solid var(--sop-border)',
            fontSize: '0.74rem',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--sop-text-muted)' }}>Step ID</span>
            <span className="sop-mono" style={{ fontWeight: 700, color: 'var(--sop-text-primary)' }}>
              STEP-{currentStep.step_number.toString().padStart(3, '0')}
            </span>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--sop-text-muted)' }}>Start Time</span>
            <span className="sop-mono" style={{ color: 'var(--sop-text-primary)' }}>
              {formatTime(currentStep.start_time)}
            </span>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--sop-text-muted)' }}>End Time</span>
            <span className="sop-mono" style={{ color: 'var(--sop-text-primary)' }}>
              {formatTime(currentStep.end_time)}
            </span>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--sop-text-muted)' }}>Duration</span>
            <span className="sop-mono" style={{ fontWeight: 600, color: '#60a5fa' }}>
              {formatDuration(durationSec)}
            </span>
          </div>
        </div>
      </div>

      {/* Tabs Row */}
      <div
        style={{
          display: 'flex',
          borderBottom: '1px solid var(--sop-border)',
          backgroundColor: 'var(--sop-bg-panel)',
          borderRadius: '6px 6px 0 0',
          padding: '0 0.5rem',
        }}
      >
        {[
          { key: 'overview', label: 'Overview' },
          { key: 'transcript', label: 'Transcript' },
          { key: 'evidence', label: `Evidence (${currentStep.evidence?.length || 4})` },
          { key: 'docs', label: 'Related Documents (2)' },
          { key: 'comments', label: 'Comments (1)' },
        ].map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key as typeof activeTab)}
            style={{
              padding: '0.75rem 1.25rem',
              fontSize: '0.8rem',
              fontWeight: 600,
              background: 'none',
              border: 'none',
              color: activeTab === tab.key ? '#3b82f6' : 'var(--sop-text-muted)',
              borderBottom: activeTab === tab.key ? '2px solid #3b82f6' : '2px solid transparent',
              cursor: 'pointer',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content: Overview with 2 Columns */}
      {activeTab === 'overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: '1.25rem' }}>
          {/* Left Column: 5 Distinct Structured Sections matching Image 2 */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
            {/* 1. Tools Required */}
            <div className="sop-card" style={{ padding: '0.85rem 1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
                <span style={{ fontSize: '1rem', color: '#10b981' }}>🔧</span>
                <span style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--sop-text-primary)' }}>
                  Tools Required
                </span>
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--sop-text-secondary)', paddingLeft: '1.5rem' }}>
                • None
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--sop-text-muted)', paddingLeft: '1.5rem', marginTop: '2px' }}>
                使用する工具: なし
              </div>
            </div>

            {/* 2. PPE Required */}
            <div className="sop-card" style={{ padding: '0.85rem 1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
                <span style={{ fontSize: '1rem', color: '#3b82f6' }}>🦺</span>
                <span style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--sop-text-primary)' }}>
                  PPE Required
                </span>
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--sop-text-secondary)', paddingLeft: '1.5rem' }}>
                • Safety gloves (recommended)
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--sop-text-muted)', paddingLeft: '1.5rem', marginTop: '2px' }}>
                必要な保護具: 保護手袋 (推奨)
              </div>
            </div>

            {/* 3. Safety Warnings (Soft Pink/Red Container matching Image 2) */}
            <div
              style={{
                padding: '0.85rem 1rem',
                borderRadius: '8px',
                backgroundColor: 'rgba(239, 68, 68, 0.08)',
                border: '1px solid rgba(239, 68, 68, 0.35)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
                <span style={{ fontSize: '1rem', color: '#ef4444' }}>⚠</span>
                <span style={{ fontSize: '0.82rem', fontWeight: 700, color: '#f87171' }}>
                  Safety Warnings
                </span>
              </div>
              <div style={{ fontSize: '0.78rem', color: '#fca5a5', paddingLeft: '1.5rem' }}>
                • Ensure machine is in idle state before turning off main switch.
              </div>
              <div style={{ fontSize: '0.72rem', color: '#f87171', paddingLeft: '1.5rem', marginTop: '3px' }}>
                安全上の注意: 主電源を切る前に、機械が停止状態であることを確認してください。
              </div>
            </div>

            {/* 4. Quality Checkpoints */}
            <div className="sop-card" style={{ padding: '0.85rem 1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
                <span style={{ fontSize: '1rem', color: '#10b981' }}>📋</span>
                <span style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--sop-text-primary)' }}>
                  Quality Checkpoints
                </span>
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--sop-text-secondary)', paddingLeft: '1.5rem' }}>
                • Indicator lamp is OFF
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--sop-text-secondary)', paddingLeft: '1.5rem', marginTop: '2px' }}>
                • No abnormal sounds
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--sop-text-muted)', paddingLeft: '1.5rem', marginTop: '3px' }}>
                品質確認項目: インジケーターランプが消えていることを確認、異常音がないことを確認
              </div>
            </div>

            {/* 5. Expected Outcome */}
            <div className="sop-card" style={{ padding: '0.85rem 1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
                <span style={{ fontSize: '1rem', color: '#8b5cf6' }}>🎯</span>
                <span style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--sop-text-primary)' }}>
                  Expected Outcome
                </span>
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--sop-text-secondary)', paddingLeft: '1.5rem' }}>
                • Machine power is completely turned off.
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--sop-text-muted)', paddingLeft: '1.5rem', marginTop: '2px' }}>
                期待される結果: 機械の電源が完全に切れた状態。
              </div>
            </div>
          </div>

          {/* Right Column: Evidence from Video (4 keyframe cards) */}
          <div className="sop-card" style={{ padding: '1rem', display: 'flex', flexDirection: 'column' }}>
            <h4 style={{ fontSize: '0.86rem', fontWeight: 700, color: 'var(--sop-text-primary)', margin: '0 0 0.85rem 0' }}>
              Evidence from Video
            </h4>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', flex: 1 }}>
              {step3Evidence.map((ev, idx) => (
                <div
                  key={idx}
                  onClick={() => seekTo(ev.timeSec)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.85rem',
                    padding: '0.5rem',
                    borderRadius: '6px',
                    backgroundColor: 'var(--sop-bg-root)',
                    border: '1px solid var(--sop-border)',
                    cursor: 'pointer',
                    transition: 'border-color 0.15s ease',
                  }}
                >
                  {/* Keyframe thumbnail */}
                  <div
                    style={{
                      width: '64px',
                      height: '48px',
                      borderRadius: '4px',
                      backgroundColor: '#1e293b',
                      flexShrink: 0,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '0.65rem',
                      color: '#94a3b8',
                      position: 'relative',
                      overflow: 'hidden',
                      border: '1px solid #334155',
                    }}
                  >
                    <div
                      style={{
                        width: '18px',
                        height: '18px',
                        borderRadius: '50%',
                        backgroundColor: idx === 3 ? '#475569' : '#ef4444',
                      }}
                    />
                  </div>

                  {/* Timestamps & Labels */}
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span className="sop-mono" style={{ fontSize: '0.74rem', fontWeight: 700, color: '#60a5fa' }}>
                      {ev.time}
                    </span>
                    <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--sop-text-primary)' }}>
                      {ev.en}
                    </span>
                    <span style={{ fontSize: '0.7rem', color: 'var(--sop-text-muted)' }}>
                      {ev.ja}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab: Transcript */}
      {activeTab === 'transcript' && (
        <div className="sop-card" style={{ padding: '1.25rem' }}>
          <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--sop-text-primary)', margin: '0 0 0.75rem 0' }}>
            Spoken Instructions for Step #{currentStep.step_number}
          </h4>
          <div style={{ padding: '0.75rem', backgroundColor: 'var(--sop-bg-root)', borderRadius: '6px', border: '1px solid var(--sop-border)' }}>
            <p className="sop-mono" style={{ color: '#60a5fa', fontSize: '0.72rem', margin: '0 0 0.4rem 0' }}>
              01:20 – 02:35 (Faster-Whisper ja)
            </p>
            <p style={{ fontSize: '0.82rem', color: 'var(--sop-text-primary)', margin: '0 0 0.4rem 0' }}>
              「それでは、主電源を切ります。操作盤のメインスイッチを確認し、OFFの位置に切り替えます。インジケーターランプが消灯していることを確認します。」
            </p>
            <p style={{ fontSize: '0.78rem', color: 'var(--sop-text-secondary)', margin: 0 }}>
              "Now, turn off the main switch. Check the main switch on the control panel, turn it to the OFF position. Confirm that the indicator lamp is completely unlit."
            </p>
          </div>
        </div>
      )}

      {/* Tab: Evidence */}
      {activeTab === 'evidence' && (
        <div className="sop-card" style={{ padding: '1.25rem' }}>
          <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--sop-text-primary)', margin: '0 0 0.75rem 0' }}>
            Empirical Video Evidence Grounding
          </h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
            {step3Evidence.map((ev, i) => (
              <div key={i} style={{ padding: '0.75rem', backgroundColor: 'var(--sop-bg-root)', borderRadius: '6px', border: '1px solid var(--sop-border)' }}>
                <div className="sop-mono" style={{ color: '#60a5fa', fontSize: '0.74rem', fontWeight: 700, marginBottom: '0.25rem' }}>
                  Timestamp: {ev.time}
                </div>
                <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--sop-text-primary)' }}>
                  {ev.en}
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--sop-text-muted)' }}>
                  {ev.ja}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab: Related Documents */}
      {activeTab === 'docs' && (
        <div className="sop-card" style={{ padding: '1.25rem' }}>
          <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--sop-text-primary)', margin: '0 0 0.75rem 0' }}>
            Linked Reference Documentation
          </h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <div style={{ padding: '0.65rem 0.85rem', backgroundColor: 'var(--sop-bg-root)', borderRadius: '6px', border: '1px solid var(--sop-border)' }}>
              📄 <strong>Machine Operation & Maintenance Manual Rev 2.1</strong> — Section 4.2: Main Power Isolation (Page 12)
            </div>
            <div style={{ padding: '0.65rem 0.85rem', backgroundColor: 'var(--sop-bg-root)', borderRadius: '6px', border: '1px solid var(--sop-border)' }}>
              📄 <strong>Plant Safety Protocol standard ISO 14118</strong> — Hazardous Energy Control (LOTO)
            </div>
          </div>
        </div>
      )}

      {/* Tab: Comments */}
      {activeTab === 'comments' && (
        <div className="sop-card" style={{ padding: '1.25rem' }}>
          <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--sop-text-primary)', margin: '0 0 0.75rem 0' }}>
            Engineering Review Notes
          </h4>
          <div style={{ padding: '0.75rem', backgroundColor: 'var(--sop-bg-root)', borderRadius: '6px', border: '1px solid var(--sop-border)' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--sop-text-muted)' }}>Lead Engineer (10/09/2026 10:18):</span>
            <p style={{ fontSize: '0.8rem', color: 'var(--sop-text-primary)', margin: '0.35rem 0 0 0' }}>
              Step verified. Power isolation complies with manufacturing safety guidelines.
            </p>
          </div>
        </div>
      )}

      {/* Bottom Section: Paired Bilingual Instructions matching Image 2 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
        {/* English Instruction Box */}
        <div className="sop-card" style={{ padding: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
              <span>📄</span>
              <span style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--sop-text-primary)' }}>
                English Instruction
              </span>
            </div>

            <button
              type="button"
              className="sop-btn sop-btn-secondary"
              onClick={() => copyToClipboard(englishInstructions.join('\n'), 'en')}
              style={{ padding: '0.25rem 0.6rem', fontSize: '0.7rem' }}
            >
              {copiedLang === 'en' ? '✓ Copied' : '📋 Copy'}
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem', fontSize: '0.78rem', color: 'var(--sop-text-primary)', lineHeight: 1.5 }}>
            {englishInstructions.map((line, idx) => (
              <div key={idx}>{line}</div>
            ))}
          </div>
        </div>

        {/* Japanese Instruction Box */}
        <div className="sop-card" style={{ padding: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
              <span>📄</span>
              <span style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--sop-text-primary)' }}>
                日本語の手順
              </span>
            </div>

            <button
              type="button"
              className="sop-btn sop-btn-secondary"
              onClick={() => copyToClipboard(japaneseInstructions.join('\n'), 'ja')}
              style={{ padding: '0.25rem 0.6rem', fontSize: '0.7rem' }}
            >
              {copiedLang === 'ja' ? '✓ コピー完了' : '📋 Copy'}
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem', fontSize: '0.78rem', color: 'var(--sop-text-primary)', lineHeight: 1.5 }}>
            {japaneseInstructions.map((line, idx) => (
              <div key={idx}>{line}</div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom Status Banner matching Image 2 */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0.75rem 1.25rem',
          borderRadius: '6px',
          backgroundColor: 'rgba(16, 185, 129, 0.12)',
          border: '1px solid rgba(16, 185, 129, 0.3)',
          fontSize: '0.76rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#10b981', fontWeight: 600 }}>
          <span>✓</span>
          <span>This step has been verified and is ready for expert review.</span>
        </div>

        <div style={{ color: 'var(--sop-text-muted)' }}>
          Last updated: 10/09/2026 10:18
        </div>
      </div>
    </div>
  );
};
