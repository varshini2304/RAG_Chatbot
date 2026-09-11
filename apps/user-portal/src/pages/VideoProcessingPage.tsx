import React, { useState, useEffect } from 'react';
import { useSopWorkflow } from '../context/WorkflowContext';
import { ProcessingPipeline } from '../components/workflow/ProcessingPipeline';
import { ProcessingLog } from '../components/workflow/ProcessingLog';
import { VideoPlayer } from '../components/video/VideoPlayer';
import { sopApi, type BackendSystemInfo } from '../services/sopApi';

interface VideoProcessingPageProps {
  onProceedToTimeline: () => void;
}

export const VideoProcessingPage: React.FC<VideoProcessingPageProps> = ({ onProceedToTimeline }) => {
  const {
    video,
    videoStreamUrl,
    fixtures,
    isIngesting,
    ingestFixtureVideo,
    uploadVideoFile,
    pipelineStages,
    logs,
    setCurrentStage,
    videoCurrentTime,
    setVideoCurrentTime,
    isPlaying,
    setIsPlaying,
    playbackRate,
    setPlaybackRate,
  } = useSopWorkflow();

  const [systemInfo, setSystemInfo] = useState<BackendSystemInfo | null>(null);
  const [showUploadModal, setShowUploadModal] = useState<boolean>(false);
  const [selectedFixture, setSelectedFixture] = useState<string>(video.filename);
  const [uploadError, setUploadError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    void sopApi.getSystemInfo().then((info) => {
      if (isMounted) setSystemInfo(info);
    });
    return () => {
      isMounted = false;
    };
  }, []);

  const formatBytes = (bytes: number): string => {
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(2)} MB`;
  };

  const formatDuration = (seconds: number): string => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      setUploadError(null);
      try {
        await uploadVideoFile(file);
        setShowUploadModal(false);
      } catch (err: unknown) {
        setUploadError(err instanceof Error ? err.message : 'Failed to ingest uploaded video.');
      }
    }
  };

  const handleSelectFixture = async (filename: string) => {
    setSelectedFixture(filename);
    try {
      await ingestFixtureVideo(filename);
      setShowUploadModal(false);
    } catch (err: unknown) {
      setUploadError(err instanceof Error ? err.message : 'Failed to ingest fixture video.');
    }
  };

  const isSilent = video.audio_codec === null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Top Main Header Card matching Image 2 */}
      <div
        className="sop-card"
        style={{
          padding: '1.25rem 1.5rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: 'var(--sop-bg-panel)',
          borderLeft: '4px solid #3b82f6',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div
            style={{
              width: '44px',
              height: '44px',
              borderRadius: '8px',
              backgroundColor: 'rgba(59, 130, 246, 0.15)',
              color: '#60a5fa',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1.4rem',
              border: '1px solid rgba(59, 130, 246, 0.3)',
            }}
          >
            🏭
          </div>
          <div>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--sop-text-primary)', margin: 0 }}>
              From Video to Work Instructions
            </h2>
            <p style={{ fontSize: '0.78rem', color: 'var(--sop-text-secondary)', margin: '0.2rem 0 0 0' }}>
              Upload a video and automatically extract, structure, and translate procedural knowledge
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button
            type="button"
            className="sop-btn sop-btn-primary"
            onClick={() => setShowUploadModal(true)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.45rem',
              padding: '0.5rem 1rem',
              fontSize: '0.8rem',
              fontWeight: 600,
            }}
          >
            <span>+</span>
            <span>Upload New Video</span>
          </button>

          <button
            type="button"
            className="sop-btn sop-btn-secondary"
            onClick={() => {
              setCurrentStage(2);
              onProceedToTimeline();
            }}
            style={{ padding: '0.5rem 1rem', fontSize: '0.8rem' }}
          >
            Proceed to Step Timeline (Phase 2) →
          </button>
        </div>
      </div>

      {/* 1. Video Upload & Processing Pipeline (Horizontal 5-Stage Stepper) */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.65rem' }}>
          <div>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--sop-text-primary)', margin: 0 }}>
              1. Video Upload & Processing Pipeline
            </h3>
            <span style={{ fontSize: '0.73rem', color: 'var(--sop-text-muted)' }}>
              Track the progress of your video through each stage of the pipeline
            </span>
          </div>
          {isIngesting && (
            <span style={{ fontSize: '0.74rem', color: '#60a5fa', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <span className="sop-spin">⟳</span> Running real video intake & audio extraction...
            </span>
          )}
        </div>

        <ProcessingPipeline stages={pipelineStages} />
      </div>

      {/* Dual Side-by-Side: Video Preview (Left) + Video Metadata (Right) */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '1.25rem' }}>
        {/* Left: Video Player / Preview */}
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <VideoPlayer
            video={video}
            streamUrl={videoStreamUrl}
            currentTime={videoCurrentTime}
            isPlaying={isPlaying}
            playbackRate={playbackRate}
            onTimeUpdate={setVideoCurrentTime}
            onPlayPause={() => setIsPlaying(!isPlaying)}
            onRateChange={setPlaybackRate}
          />
        </div>

        {/* Right: Video Metadata Card matching Image 2 */}
        <div className="sop-card" style={{ display: 'flex', flexDirection: 'column' }}>
          <div className="sop-card-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span className="sop-mono" style={{ fontSize: '0.92rem', fontWeight: 700, color: 'var(--sop-text-primary)' }}>
                {video.filename}
              </span>
              <button
                type="button"
                onClick={() => setShowUploadModal(true)}
                title="Change or re-ingest video"
                style={{ background: 'none', border: 'none', color: '#60a5fa', cursor: 'pointer', fontSize: '0.85rem' }}
              >
                ✏
              </button>
            </div>
            <span className="sop-badge sop-badge-teal">Container Validated</span>
          </div>

          <div className="sop-card-body" style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            {/* 2-Column Metadata Grid matching Image 2 */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', paddingBottom: '1rem' }}>
              {/* Left Column: Container Technical Specs */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: '0.7rem', color: 'var(--sop-text-muted)' }}>File size</span>
                  <span className="sop-mono" style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--sop-text-primary)' }}>
                    {formatBytes(video.size_bytes)}
                  </span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: '0.7rem', color: 'var(--sop-text-muted)' }}>Duration</span>
                  <span className="sop-mono" style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--sop-text-primary)' }}>
                    {formatDuration(video.duration_sec)} ({video.duration_sec.toFixed(0)} sec)
                  </span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: '0.7rem', color: 'var(--sop-text-muted)' }}>Resolution</span>
                  <span className="sop-mono" style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--sop-text-primary)' }}>
                    {video.width} × {video.height}
                  </span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: '0.7rem', color: 'var(--sop-text-muted)' }}>Video codec</span>
                  <span className="sop-mono" style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--sop-text-primary)' }}>
                    {video.codec.toUpperCase()}
                  </span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: '0.7rem', color: 'var(--sop-text-muted)' }}>Audio codec</span>
                  <span className="sop-mono" style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--sop-text-primary)' }}>
                    {isSilent ? 'None (Silent Recording)' : `${video.audio_codec?.toUpperCase()} (${video.audio_channels === 2 ? 'stereo' : 'mono'}, ${((video.sample_rate || 48000) / 1000).toFixed(0)} kHz)`}
                  </span>
                </div>
              </div>

              {/* Right Column: High-Level Processing Status */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', borderLeft: '1px solid var(--sop-border-subtle)', paddingLeft: '1rem' }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.6rem' }}>
                  <div style={{ fontSize: '1.2rem', color: '#60a5fa' }}>🌐</div>
                  <div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--sop-text-muted)' }}>Detected Language</div>
                    <div style={{ fontSize: '0.84rem', fontWeight: 700, color: 'var(--sop-text-primary)' }}>
                      {isSilent ? 'Visual Only (N/A)' : 'Japanese (ja)'}
                    </div>
                    {!isSilent && (
                      <div style={{ fontSize: '0.7rem', color: 'var(--sop-teal)' }}>
                        Confidence: 0.9839
                      </div>
                    )}
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.6rem' }}>
                  <div style={{ fontSize: '1.2rem', color: '#60a5fa' }}>📋</div>
                  <div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--sop-text-muted)' }}>Estimated Work Steps</div>
                    <div style={{ fontSize: '0.84rem', fontWeight: 700, color: 'var(--sop-text-primary)' }}>
                      12 steps
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.6rem' }}>
                  <div style={{ fontSize: '1.2rem', color: '#60a5fa' }}>
                    <span className="sop-spin" style={{ display: 'inline-block' }}>⟳</span>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--sop-text-muted)' }}>Status</div>
                    <div style={{ fontSize: '0.84rem', fontWeight: 600, color: '#93c5fd' }}>
                      {isSilent ? 'Visual step segmentation ready' : 'Transcribing audio...'}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Strict Notice for Silent Videos */}
            {isSilent && (
              <div className="sop-callout sop-callout-warning" style={{ marginTop: '0.5rem' }}>
                <div>
                  <strong>Cleanroom / Silent Video:</strong> No audio stream detected. Audio extraction and speech transcription (ASR) are automatically marked as <strong>Skipped</strong>.
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Chronological Processing Log [Live] */}
      <div>
        <ProcessingLog logs={logs} />
      </div>

      {/* System Information (4 Cards) matching Image 2 */}
      <div>
        <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--sop-text-primary)', marginBottom: '0.65rem' }}>
          System Information
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
          {/* Card 1: ASR Model */}
          <div
            className="sop-card"
            style={{ padding: '0.85rem 1rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}
          >
            <div style={{ fontSize: '1.35rem', color: '#60a5fa' }}>🛡</div>
            <div>
              <div style={{ fontSize: '0.7rem', color: 'var(--sop-text-muted)' }}>ASR Model</div>
              <div style={{ fontSize: '0.84rem', fontWeight: 700, color: 'var(--sop-text-primary)' }}>
                {systemInfo?.asr_model?.name ?? 'faster-whisper (base)'}
              </div>
              <div className="sop-mono" style={{ fontSize: '0.68rem', color: 'var(--sop-text-secondary)' }}>
                {systemInfo?.asr_model?.details ?? 'int8 • CPU'}
              </div>
            </div>
          </div>

          {/* Card 2: Audio Format */}
          <div
            className="sop-card"
            style={{ padding: '0.85rem 1rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}
          >
            <div style={{ fontSize: '1.35rem', color: '#10b981' }}>🔊</div>
            <div>
              <div style={{ fontSize: '0.7rem', color: 'var(--sop-text-muted)' }}>Audio Format</div>
              <div style={{ fontSize: '0.84rem', fontWeight: 700, color: 'var(--sop-text-primary)' }}>
                {systemInfo?.audio_format?.name ?? 'WAV • 16 kHz • Mono'}
              </div>
              <div className="sop-mono" style={{ fontSize: '0.68rem', color: 'var(--sop-text-secondary)' }}>
                {systemInfo?.audio_format?.encoding ?? 'PCM 16-bit'}
              </div>
            </div>
          </div>

          {/* Card 3: Target Languages */}
          <div
            className="sop-card"
            style={{ padding: '0.85rem 1rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}
          >
            <div style={{ fontSize: '1.35rem', color: '#f59e0b' }}>🌐</div>
            <div>
              <div style={{ fontSize: '0.7rem', color: 'var(--sop-text-muted)' }}>Target Languages</div>
              <div style={{ fontSize: '0.84rem', fontWeight: 700, color: 'var(--sop-text-primary)' }}>
                {systemInfo?.target_languages?.primary ?? 'Japanese (ja)'}
              </div>
              <div style={{ fontSize: '0.68rem', color: 'var(--sop-text-secondary)' }}>
                {systemInfo?.target_languages?.secondary ?? 'English (en)'}
              </div>
            </div>
          </div>

          {/* Card 4: Processing Mode */}
          <div
            className="sop-card"
            style={{ padding: '0.85rem 1rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}
          >
            <div style={{ fontSize: '1.35rem', color: '#8b5cf6' }}>⚙</div>
            <div>
              <div style={{ fontSize: '0.7rem', color: 'var(--sop-text-muted)' }}>Processing Mode</div>
              <div style={{ fontSize: '0.84rem', fontWeight: 700, color: 'var(--sop-text-primary)' }}>
                {systemInfo?.processing_mode?.name ?? 'Standard'}
              </div>
              <div style={{ fontSize: '0.68rem', color: 'var(--sop-text-secondary)' }}>
                {systemInfo?.processing_mode?.subtitle ?? '(High Accuracy)'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Upload Video & Benchmark Selector Modal */}
      {showUploadModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
          }}
          onClick={() => setShowUploadModal(false)}
        >
          <div
            className="sop-card"
            style={{
              width: '90%',
              maxWidth: '540px',
              padding: '1.5rem',
              backgroundColor: 'var(--sop-bg-panel)',
              border: '1px solid var(--sop-border-focus)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
              <h3 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--sop-text-primary)', margin: 0 }}>
                Select or Upload Manufacturing Video
              </h3>
              <button
                type="button"
                onClick={() => setShowUploadModal(false)}
                style={{ background: 'none', border: 'none', color: 'var(--sop-text-muted)', cursor: 'pointer', fontSize: '1.2rem' }}
              >
                ✕
              </button>
            </div>

            {/* Option A: Upload file from computer */}
            <div style={{ marginBottom: '1.25rem' }}>
              <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--sop-text-secondary)', marginBottom: '0.45rem' }}>
                Upload Local Video File
              </div>
              <label
                className="sop-btn sop-btn-secondary"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.5rem',
                  cursor: 'pointer',
                  padding: '0.75rem',
                  border: '2px dashed var(--sop-border)',
                  borderRadius: '6px',
                  backgroundColor: 'var(--sop-bg-root)',
                }}
              >
                <span>📤 Choose MP4, MOV, AVI, MKV, or WEBM</span>
                <input
                  type="file"
                  accept=".mp4,.mov,.avi,.mkv,.webm"
                  onChange={handleFileUpload}
                  style={{ display: 'none' }}
                />
              </label>
            </div>

            {/* Option B: Choose server benchmark video fixtures */}
            {fixtures.length > 0 && (
              <div>
                <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--sop-text-secondary)', marginBottom: '0.45rem' }}>
                  Or Select Server Benchmark Fixture:
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', maxHeight: '200px', overflowY: 'auto' }}>
                  {fixtures.map((f) => (
                    <button
                      key={f.filename}
                      type="button"
                      onClick={() => handleSelectFixture(f.filename)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '0.55rem 0.75rem',
                        backgroundColor: selectedFixture === f.filename ? 'var(--sop-bg-hover)' : 'var(--sop-bg-root)',
                        border: '1px solid',
                        borderColor: selectedFixture === f.filename ? '#3b82f6' : 'var(--sop-border)',
                        borderRadius: '6px',
                        color: 'var(--sop-text-primary)',
                        cursor: 'pointer',
                        textAlign: 'left',
                      }}
                    >
                      <span className="sop-mono" style={{ fontSize: '0.76rem', fontWeight: 600 }}>
                        {f.filename}
                      </span>
                      <span className="sop-mono" style={{ fontSize: '0.7rem', color: 'var(--sop-text-muted)' }}>
                        {(f.size_bytes / (1024 * 1024)).toFixed(2)} MB
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {uploadError && (
              <div style={{ color: '#ef4444', fontSize: '0.74rem', marginTop: '0.75rem' }}>
                {uploadError}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
