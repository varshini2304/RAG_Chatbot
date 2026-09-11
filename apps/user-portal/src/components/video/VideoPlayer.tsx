import React, { useRef, useEffect, useState } from 'react';
import type { VideoMetadata, WorkStep } from '../../types/sop';

import { sopApi } from '../../services/sopApi';

interface VideoPlayerProps {
  video: VideoMetadata;
  currentTime: number;
  isPlaying: boolean;
  playbackRate: number;
  streamUrl?: string;
  steps?: WorkStep[];
  currentStep?: WorkStep;
  onTimeUpdate: (timeSec: number) => void;
  onPlayPause: () => void;
  onRateChange: (rate: number) => void;
  onStepClick?: (stepId: string, startTime: number) => void;
}

export const VideoPlayer: React.FC<VideoPlayerProps> = ({
  video,
  currentTime,
  isPlaying,
  playbackRate,
  streamUrl,
  steps = [],
  currentStep,
  onTimeUpdate,
  onPlayPause,
  onRateChange,
  onStepClick,
}) => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [videoError, setVideoError] = useState<boolean>(false);

  const effectiveStreamUrl =
    streamUrl ||
    sopApi.getStreamUrl(video.filename) ||
    `http://localhost:8000/api/v1/video/stream/${encodeURIComponent(video.filename)}`;

  const isSilent = video.audio_codec === null;

  // Whenever streamUrl or filename changes, reset error state
  useEffect(() => {
    setVideoError(false);
  }, [effectiveStreamUrl, video.filename]);

  // Format seconds to mm:ss
  const formatTime = (seconds: number): string => {
    const totalSec = Math.max(0, Math.floor(seconds));
    const m = Math.floor(totalSec / 60);
    const s = totalSec % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  // Synchronize HTML5 video with state
  useEffect(() => {
    const v = videoRef.current;
    if (!v || videoError) return;

    if (isPlaying && v.paused) {
      void v.play().catch(() => {
        // Autoplay policy or format fallback
      });
    } else if (!isPlaying && !v.paused) {
      v.pause();
    }
  }, [isPlaying, videoError]);

  useEffect(() => {
    const v = videoRef.current;
    if (!v || videoError) return;
    v.playbackRate = playbackRate;
  }, [playbackRate, videoError]);

  useEffect(() => {
    const v = videoRef.current;
    if (!v || videoError) return;
    if (Math.abs(v.currentTime - currentTime) > 1.0) {
      v.currentTime = currentTime;
    }
  }, [currentTime, videoError]);

  // Fallback simulation timer if using canvas
  useEffect(() => {
    if (!videoError) return;
    let interval: number;
    if (isPlaying) {
      interval = window.setInterval(() => {
        onTimeUpdate(Math.min(video.duration_sec, currentTime + 0.5 * playbackRate));
        if (currentTime >= video.duration_sec) {
          onPlayPause();
        }
      }, 500);
    }
    return () => clearInterval(interval);
  }, [isPlaying, currentTime, video.duration_sec, playbackRate, onTimeUpdate, onPlayPause, videoError]);

  // Render technical overlay canvas if video error or idle
  useEffect(() => {
    if (!videoError) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;

    const grad = ctx.createLinearGradient(0, 0, width, height);
    grad.addColorStop(0, '#0a0e1c');
    grad.addColorStop(0.5, '#12182b');
    grad.addColorStop(1, '#080c18');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, width, height);

    // Subtle technical grid
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
    ctx.lineWidth = 1;
    for (let x = 0; x < width; x += 40) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    for (let y = 0; y < height; y += 40) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    // Reticle
    const cx = width / 2;
    const cy = height / 2;
    ctx.strokeStyle = 'rgba(59, 130, 246, 0.5)';
    ctx.beginPath();
    ctx.moveTo(cx - 20, cy);
    ctx.lineTo(cx + 20, cy);
    ctx.moveTo(cx, cy - 20);
    ctx.lineTo(cx, cy + 20);
    ctx.stroke();

    // Telemetry text
    ctx.fillStyle = 'rgba(255, 255, 255, 0.85)';
    ctx.font = '12px var(--sop-font-mono, monospace)';
    ctx.fillText(`CAM-01 [${video.codec.toUpperCase()} / ${video.width}x${video.height}]`, 18, 28);
    ctx.fillText(`TIMECODE: ${formatTime(currentTime)} / ${formatTime(video.duration_sec)}`, 18, 46);
    ctx.fillText(`FRAME: ${Math.floor(currentTime * (video.fps || 25))}`, 18, 64);
  }, [currentTime, isPlaying, video, currentStep, videoError]);

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    onTimeUpdate(val);
    if (videoRef.current && !videoError) {
      videoRef.current.currentTime = val;
    }
  };

  return (
    <div
      className="sop-video-player-root"
      ref={containerRef}
      style={{
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: '#070911',
        borderRadius: '8px',
        overflow: 'hidden',
        border: '1px solid var(--sop-border)',
        boxShadow: '0 4px 20px rgba(0,0,0,0.4)',
      }}
    >
      {/* Video / Canvas Viewport */}
      <div
        style={{
          position: 'relative',
          width: '100%',
          aspectRatio: '16/9',
          backgroundColor: '#000000',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          overflow: 'hidden',
        }}
      >
        {!videoError ? (
          <video
            ref={videoRef}
            key={effectiveStreamUrl}
            src={effectiveStreamUrl}
            muted={isSilent}
            playsInline
            preload="auto"
            onLoadedMetadata={() => setVideoError(false)}
            onCanPlay={() => setVideoError(false)}
            onTimeUpdate={(e) => onTimeUpdate(e.currentTarget.currentTime)}
            onEnded={() => onPlayPause()}
            onError={(e) => {
              console.warn('Live video stream not reachable at:', effectiveStreamUrl, e);
              setVideoError(true);
            }}
            style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }}
            onClick={onPlayPause}
          />
        ) : (
          <>
            <canvas
              ref={canvasRef}
              width={800}
              height={450}
              style={{ width: '100%', height: '100%', display: 'block', cursor: 'pointer' }}
              onClick={onPlayPause}
            />
            <div
              style={{
                position: 'absolute',
                top: '12px',
                left: '12px',
                right: '12px',
                padding: '6px 10px',
                backgroundColor: 'rgba(239, 68, 68, 0.88)',
                borderRadius: '6px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                color: '#fff',
                fontSize: '0.72rem',
                zIndex: 20,
              }}
            >
              <span>⚠ Video stream failed to load from: <strong className="sop-mono">{effectiveStreamUrl}</strong></span>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setVideoError(false);
                }}
                style={{
                  padding: '3px 8px',
                  borderRadius: '4px',
                  backgroundColor: '#fff',
                  color: '#dc2626',
                  border: 'none',
                  fontWeight: 700,
                  cursor: 'pointer',
                  fontSize: '0.7rem',
                }}
              >
                Retry ⟳
              </button>
            </div>
          </>
        )}

        {/* Center Play Button Overlay when Paused */}
        {!isPlaying && (
          <button
            type="button"
            onClick={onPlayPause}
            aria-label="Play video"
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              width: '64px',
              height: '64px',
              borderRadius: '50%',
              backgroundColor: 'rgba(15, 23, 42, 0.85)',
              border: '2px solid rgba(255, 255, 255, 0.35)',
              color: '#ffffff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1.75rem',
              cursor: 'pointer',
              backdropFilter: 'blur(6px)',
              transition: 'transform 0.15s ease, background-color 0.15s ease',
              zIndex: 10,
            }}
          >
            <span style={{ marginLeft: '4px' }}>▶</span>
          </button>
        )}

        {/* Current Step Banner Overlay (bottom of video viewport) */}
        {currentStep && (
          <div
            style={{
              position: 'absolute',
              bottom: '12px',
              left: '16px',
              right: '16px',
              padding: '8px 14px',
              backgroundColor: 'rgba(11, 15, 28, 0.88)',
              border: '1px solid rgba(59, 130, 246, 0.4)',
              borderRadius: '6px',
              backdropFilter: 'blur(6px)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              zIndex: 5,
            }}
          >
            <div>
              <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#93c5fd', textTransform: 'uppercase' }}>
                Step {currentStep.step_number}: {currentStep.title}
              </span>
              {currentStep.title_ja && (
                <span style={{ fontSize: '0.72rem', color: '#94a3b8', marginLeft: '0.5rem' }}>
                  ({currentStep.title_ja})
                </span>
              )}
            </div>

            <span className="sop-mono" style={{ fontSize: '0.7rem', color: '#60a5fa' }}>
              {formatTime(currentStep.start_time)} – {formatTime(currentStep.end_time)}
            </span>
          </div>
        )}
      </div>

      {/* Scrub Bar with Step Range Markers */}
      <div
        style={{
          position: 'relative',
          padding: '0 0.75rem',
          backgroundColor: 'var(--sop-bg-surface)',
          borderTop: '1px solid var(--sop-border-subtle)',
        }}
      >
        {/* Step Marker Ticks */}
        <div style={{ position: 'absolute', top: 0, left: '0.75rem', right: '0.75rem', height: '5px' }}>
          {steps.map((step) => {
            const leftPct = (step.start_time / (video.duration_sec || 1)) * 100;
            const widthPct = ((step.end_time - step.start_time) / (video.duration_sec || 1)) * 100;
            const isCurrent = currentStep?.id === step.id;

            return (
              <div
                key={step.id}
                title={`Step ${step.step_number}: ${step.title}`}
                onClick={(e) => {
                  e.stopPropagation();
                  onStepClick?.(step.id, step.start_time);
                }}
                style={{
                  position: 'absolute',
                  left: `${leftPct}%`,
                  width: `${widthPct}%`,
                  height: '4px',
                  backgroundColor: isCurrent ? '#3b82f6' : 'rgba(100, 116, 139, 0.45)',
                  borderRight: '1px solid #1e243d',
                  cursor: 'pointer',
                }}
              />
            );
          })}
        </div>

        <input
          type="range"
          min={0}
          max={video.duration_sec || 100}
          step={0.5}
          value={currentTime}
          onChange={handleSeek}
          aria-label="Seek Video Timeline"
          style={{
            width: '100%',
            accentColor: '#3b82f6',
            cursor: 'pointer',
            margin: '0.5rem 0',
            display: 'block',
          }}
        />
      </div>

      {/* Playback Controls Footer */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0.5rem 0.85rem',
          backgroundColor: 'var(--sop-bg-panel)',
          fontSize: '0.75rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <button
            type="button"
            className="sop-btn sop-btn-secondary"
            onClick={onPlayPause}
            style={{ padding: '0.3rem 0.65rem', fontSize: '0.75rem' }}
          >
            {isPlaying ? '⏸ Pause' : '▶ Play'}
          </button>

          <button
            type="button"
            className="sop-btn sop-btn-secondary"
            onClick={() => onTimeUpdate(Math.max(0, currentTime - 5))}
            title="Rewind 5 seconds"
            style={{ padding: '0.3rem 0.5rem', fontSize: '0.72rem' }}
          >
            -5s
          </button>

          <button
            type="button"
            className="sop-btn sop-btn-secondary"
            onClick={() => onTimeUpdate(Math.min(video.duration_sec, currentTime + 5))}
            title="Forward 5 seconds"
            style={{ padding: '0.3rem 0.5rem', fontSize: '0.72rem' }}
          >
            +5s
          </button>

          <span className="sop-mono" style={{ color: 'var(--sop-text-secondary)', marginLeft: '0.4rem' }}>
            <strong style={{ color: 'var(--sop-text-primary)' }}>{formatTime(currentTime)}</strong> / {formatTime(video.duration_sec)}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {isSilent ? (
            <span
              className="sop-badge sop-badge-amber"
              title="FFprobe detected zero audio streams. ASR is skipped and visual analysis is primary."
            >
              🔇 Audio: None (Silent)
            </span>
          ) : (
            <span
              className="sop-badge sop-badge-teal"
              title={`Audio Stream: ${video.audio_codec?.toUpperCase()} (${video.sample_rate || 48000} Hz)`}
            >
              🔊 Audio: {video.audio_codec?.toUpperCase()} 48 kHz
            </span>
          )}

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <span style={{ color: 'var(--sop-text-muted)', fontSize: '0.7rem' }}>Speed:</span>
            {[1, 1.5, 2].map((rate) => (
              <button
                key={rate}
                type="button"
                onClick={() => onRateChange(rate)}
                style={{
                  padding: '0.2rem 0.4rem',
                  borderRadius: '3px',
                  fontSize: '0.68rem',
                  fontWeight: playbackRate === rate ? 700 : 500,
                  backgroundColor: playbackRate === rate ? 'var(--sop-bg-elevated)' : 'transparent',
                  color: playbackRate === rate ? '#93c5fd' : 'var(--sop-text-muted)',
                  border: '1px solid',
                  borderColor: playbackRate === rate ? 'var(--sop-blue-border)' : 'transparent',
                }}
              >
                {rate}x
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
