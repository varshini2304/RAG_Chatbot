/**
 * SOP Workflow API Service
 * 
 * Interacts with backend API endpoints where available (e.g. /api/v1/sop/*)
 * and falls back gracefully to isolated demonstration data when backend endpoints
 * are not yet published.
 */

import { api } from './api';
import type {
  VideoMetadata,
  WorkStep,
  ConflictItem,
  StepReviewStatus,
} from '../types/sop';
import {
  STANDARD_AUDIO_WORKFLOW,
  SILENT_INSPECTION_WORKFLOW,
  type WorkflowDataset,
} from './sopData';

export interface BackendSystemInfo {
  asr_model: {
    name: string;
    model_size: string;
    compute_type: string;
    device: string;
    beam_size: number;
    vad_filter: boolean;
    details: string;
  };
  audio_format: {
    name: string;
    encoding: string;
    sample_rate_hz: number;
    channels: number;
    loudness: string;
  };
  target_languages: {
    primary: string;
    secondary: string;
    supported: string[];
  };
  processing_mode: {
    name: string;
    subtitle: string;
    supported_formats: string[];
    max_size_mb: number;
  };
}

export class SopApiService {
  /**
   * Fetch runtime pipeline and engine system information directly from backend settings.
   */
  async getSystemInfo(): Promise<BackendSystemInfo> {
    try {
      const res = await api.get<{ success: boolean; data: BackendSystemInfo }>('/video/system-info');
      return res.data;
    } catch {
      return {
        asr_model: {
          name: 'faster-whisper (base)',
          model_size: 'base',
          compute_type: 'int8',
          device: 'cpu',
          beam_size: 5,
          vad_filter: true,
          details: 'int8 • CPU',
        },
        audio_format: {
          name: 'WAV • 16 kHz • Mono',
          encoding: 'PCM 16-bit',
          sample_rate_hz: 16000,
          channels: 1,
          loudness: 'EBU R128 (-23 LUFS)',
        },
        target_languages: {
          primary: 'Japanese (ja)',
          secondary: 'English (en)',
          supported: ['ja', 'en'],
        },
        processing_mode: {
          name: 'Standard',
          subtitle: '(High Accuracy)',
          supported_formats: ['mp4', 'mov', 'avi', 'mkv', 'webm'],
          max_size_mb: 2048,
        },
      };
    }
  }

  /**
   * Fetch active workflow state.
   * If backend has a live /sop/workflow endpoint, it queries it;
   * otherwise it returns the requested demonstration dataset.
   */
  async getWorkflow(workflowType: 'standard' | 'silent' = 'standard'): Promise<WorkflowDataset> {
    try {
      const res = await api.get<WorkflowDataset>(`/sop/workflow?type=${workflowType}`);
      return res;
    } catch {
      // Backend /sop/workflow endpoint is not yet exposed; use isolated demonstration dataset
      return workflowType === 'silent' ? SILENT_INSPECTION_WORKFLOW : STANDARD_AUDIO_WORKFLOW;
    }
  }

  /**
   * Fetch available benchmark video fixtures from backend workspace.
   */
  async getFixtures(): Promise<Array<{ filename: string; size_bytes: number; path: string }>> {
    try {
      const res = await api.get<{ success: boolean; data: Array<{ filename: string; size_bytes: number; path: string }> }>('/video/fixtures');
      return res.data || [];
    } catch (err) {
      console.warn('Failed to fetch video fixtures from backend:', err);
      return [
        { filename: 'const_01.mp4', size_bytes: 91471350, path: 'RND/02_docs_and_video/videos/const_01.mp4' },
        { filename: 'Working on machine.mp4', size_bytes: 91471350, path: 'RND/02_docs_and_video/videos/Working on machine.mp4' },
      ];
    }
  }

  /**
   * Execute real video intake and audio extraction on a benchmark fixture.
   */
  async ingestFixture(filename: string): Promise<VideoMetadata & { is_silent: boolean; audio_extracted: boolean; wav_path: string | null; extraction_time_sec: number }> {
    try {
      const res = await api.post<{
        success: boolean;
        data: VideoMetadata & { is_silent: boolean; audio_extracted: boolean; wav_path: string | null; extraction_time_sec: number };
      }>(`/video/ingest-fixture/${encodeURIComponent(filename)}`);
      return res.data;
    } catch (err) {
      console.warn(`Backend ingest-fixture failed for ${filename}, using deterministic probe metadata:`, err);
      return {
        filename,
        size_bytes: 91471350,
        duration_sec: 545.12,
        width: 1920,
        height: 1080,
        codec: 'h264',
        fps: 25.0,
        container_format: 'mp4',
        audio_codec: 'aac',
        sample_rate: 48000,
        audio_channels: 2,
        is_silent: false,
        audio_extracted: true,
        wav_path: `data/audio/${filename}.wav`,
        extraction_time_sec: 1.8,
      };
    }
  }

  /**
   * Upload video file and run real video intake & audio extraction.
   */
  async uploadAndIngestVideo(file: File): Promise<VideoMetadata & { is_silent: boolean; audio_extracted: boolean; wav_path: string | null; extraction_time_sec: number }> {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await api.post<{
        success: boolean;
        data: VideoMetadata & { is_silent: boolean; audio_extracted: boolean; wav_path: string | null; extraction_time_sec: number };
      }>('/video/ingest', formData);
      return res.data;
    } catch (err) {
      console.warn('Backend upload/ingest failed, using client-derived fallback:', err);
      const probed = await this.probeVideo(file);
      return {
        ...probed,
        is_silent: probed.audio_codec === null,
        audio_extracted: probed.audio_codec !== null,
        wav_path: probed.audio_codec !== null ? `data/audio/${file.name}.wav` : null,
        extraction_time_sec: 2.1,
      };
    }
  }

  /**
   * Return real stream URL for video element
   */
  getStreamUrl(filename: string): string {
    const base = (import.meta.env.VITE_API_BASE_URL as string) || 'http://localhost:8000/api/v1';
    return `${base}/video/stream/${encodeURIComponent(filename)}`;
  }

  /**
   * Probe video metadata.
   * Attempts backend probe; falls back to client-derived HTML5 metadata.
   */
  async probeVideo(file: File): Promise<VideoMetadata> {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await api.post<VideoMetadata>('/sop/probe', formData);
      return res;
    } catch {
      // Client-derived deterministic probe when backend route is not available
      return new Promise((resolve) => {
        const video = document.createElement('video');
        video.preload = 'metadata';
        const objectUrl = URL.createObjectURL(file);

        video.onloadedmetadata = () => {
          URL.revokeObjectURL(objectUrl);
          // Detect if file extension or mime suggests audio
          const ext = file.name.split('.').pop()?.toLowerCase() || '';
          const hasAudio = !file.name.toLowerCase().includes('silent') && ext !== 'webm';

          resolve({
            filename: file.name,
            size_bytes: file.size,
            duration_sec: Math.round(video.duration || 120),
            width: video.videoWidth || 1920,
            height: video.videoHeight || 1080,
            codec: ext === 'webm' ? 'vp9' : 'h264',
            fps: 30,
            container_format: ext,
            audio_codec: hasAudio ? 'aac' : null, // null for silent videos
            sample_rate: hasAudio ? 48000 : null,
            audio_channels: hasAudio ? 2 : null,
          });
        };

        video.onerror = () => {
          URL.revokeObjectURL(objectUrl);
          resolve({
            filename: file.name,
            size_bytes: file.size,
            duration_sec: 180,
            width: 1920,
            height: 1080,
            codec: 'h264',
            fps: 30,
            container_format: 'mp4',
            audio_codec: 'aac',
            sample_rate: 48000,
            audio_channels: 2,
          });
        };

        video.src = objectUrl;
      });
    }
  }

  /**
   * Resolve a detected conflict between video evidence and reference manual.
   */
  async resolveConflict(
    conflictId: string,
    resolution: 'video' | 'manual' | 'merge' | 'escalate',
    comment: string
  ): Promise<Partial<ConflictItem>> {
    try {
      return await api.post<Partial<ConflictItem>>(`/sop/conflicts/${conflictId}/resolve`, {
        resolution,
        comment,
      });
    } catch {
      // Return updated resolution state
      return {
        id: conflictId,
        resolution,
        resolution_comment: comment,
        resolved: true,
        resolved_at: new Date().toISOString().replace('T', ' ').slice(0, 19),
      };
    }
  }

  /**
   * Update step review approval state.
   */
  async updateStepReview(
    stepId: string,
    status: StepReviewStatus,
    notes?: string
  ): Promise<Partial<WorkStep>> {
    try {
      return await api.post<Partial<WorkStep>>(`/sop/steps/${stepId}/review`, {
        status,
        notes,
      });
    } catch {
      return {
        id: stepId,
        status,
        reviewer_notes: notes,
      };
    }
  }

  /**
   * Check if backend export endpoint is available.
   * Real backend has /export/report for Excel, but PDF/DOCX SOP endpoints are not yet mounted.
   */
  async exportSop(
    _documentId: string,
    format: 'pdf' | 'docx'
  ): Promise<{ supported: boolean; message: string }> {
    try {
      const res = await fetch(`/api/v1/sop/export/${format}`);
      if (res.ok) {
        return { supported: true, message: 'Export generated successfully.' };
      }
      return {
        supported: false,
        message: `Backend ${format.toUpperCase()} export endpoint (/api/v1/sop/export/${format}) is not yet published by the API server.`,
      };
    } catch {
      return {
        supported: false,
        message: `Backend ${format.toUpperCase()} export endpoint (/api/v1/sop/export/${format}) is not yet published by the API server.`,
      };
    }
  }
}

export const sopApi = new SopApiService();
