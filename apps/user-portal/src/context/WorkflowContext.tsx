import React, { createContext, useContext, useEffect, useState } from 'react';
import type {
  WorkflowStageNumber,
  VideoMetadata,
  PipelineStageInfo,
  ProcessingLogEntry,
  WorkStep,
  ConflictItem,
  SOPDocument,
  StepReviewStatus,
} from '../types/sop';
import {
  STANDARD_AUDIO_WORKFLOW,
  SILENT_INSPECTION_WORKFLOW,
  type WorkflowDataset,
} from '../services/sopData';
import { sopApi } from '../services/sopApi';

export interface VideoFixture {
  filename: string;
  size_bytes: number;
  path: string;
}

interface WorkflowContextType {
  currentStage: WorkflowStageNumber;
  setCurrentStage: (stage: WorkflowStageNumber) => void;
  activeDatasetType: 'standard' | 'silent';
  switchDataset: (type: 'standard' | 'silent') => void;
  video: VideoMetadata;
  videoStreamUrl: string;
  fixtures: VideoFixture[];
  isIngesting: boolean;
  ingestFixtureVideo: (filename: string) => Promise<void>;
  uploadVideoFile: (file: File) => Promise<void>;
  pipelineStages: PipelineStageInfo[];
  logs: ProcessingLogEntry[];
  steps: WorkStep[];
  conflicts: ConflictItem[];
  document: SOPDocument;
  selectedStepId: string;
  setSelectedStepId: (id: string) => void;
  videoCurrentTime: number;
  setVideoCurrentTime: (time: number) => void;
  isPlaying: boolean;
  setIsPlaying: (playing: boolean) => void;
  playbackRate: number;
  setPlaybackRate: (rate: number) => void;
  seekTo: (timeSec: number) => void;
  resolveConflict: (conflictId: string, resolution: 'video' | 'manual' | 'merge' | 'escalate', comment: string) => Promise<void>;
  updateStepReview: (stepId: string, status: StepReviewStatus, notes?: string) => Promise<void>;
  allStepsApproved: boolean;
  approvedCount: number;
  totalStepsCount: number;
  hasUnresolvedConflicts: boolean;
}

const WorkflowContext = createContext<WorkflowContextType | undefined>(undefined);

export const WorkflowProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [activeDatasetType, setActiveDatasetType] = useState<'standard' | 'silent'>('standard');
  const [currentStage, setCurrentStage] = useState<WorkflowStageNumber>(1);

  // Initialize from benchmark dataset (const_01.mp4)
  const [dataset, setDataset] = useState<WorkflowDataset>(STANDARD_AUDIO_WORKFLOW);
  const [selectedStepId, setSelectedStepId] = useState<string>(STANDARD_AUDIO_WORKFLOW.steps[0]?.id || '');
  const [videoCurrentTime, setVideoCurrentTime] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playbackRate, setPlaybackRate] = useState<number>(1);
  const [videoStreamUrl, setVideoStreamUrl] = useState<string>(sopApi.getStreamUrl('const_01.mp4'));
  const [fixtures, setFixtures] = useState<VideoFixture[]>([]);
  const [isIngesting, setIsIngesting] = useState<boolean>(false);

  // Load available server video fixtures on mount
  useEffect(() => {
    let isMounted = true;
    const loadFixtures = async () => {
      const items = await sopApi.getFixtures();
      if (isMounted && items.length > 0) {
        setFixtures(items);
        const const01 = items.find((f) => f.filename === 'const_01.mp4');
        if (const01) {
          setVideoStreamUrl(sopApi.getStreamUrl(const01.filename));
        }
      }
    };
    void loadFixtures();
    return () => {
      isMounted = false;
    };
  }, []);

  const switchDataset = (type: 'standard' | 'silent') => {
    setActiveDatasetType(type);
    const chosen = type === 'silent' ? SILENT_INSPECTION_WORKFLOW : STANDARD_AUDIO_WORKFLOW;
    setDataset(chosen);
    setSelectedStepId(chosen.steps[0]?.id || '');
    setVideoCurrentTime(0);
    setIsPlaying(false);
    setVideoStreamUrl(sopApi.getStreamUrl(chosen.video.filename));
  };

  /**
   * Run real backend Video Ingestion and Audio Extraction for a fixture
   */
  const ingestFixtureVideo = async (filename: string) => {
    setIsIngesting(true);
    try {
      const res = await sopApi.ingestFixture(filename);
      const nowTime = new Date().toTimeString().slice(0, 8);

      const newLogs: ProcessingLogEntry[] = [
        {
          id: `log_intake_${Date.now()}`,
          timestamp: nowTime,
          stage: 'Video Intake',
          message: `File validation completed: ${res.width}x${res.height} @ ${res.fps} fps (${res.codec.toUpperCase()}), ${(res.size_bytes / (1024 * 1024)).toFixed(2)} MB`,
          status: 'success',
        },
        {
          id: `log_audio_${Date.now()}`,
          timestamp: nowTime,
          stage: 'Audio Extraction',
          message: res.is_silent
            ? 'FFprobe confirmed zero audio tracks. Audio extraction skipped.'
            : `Audio extracted (${res.sample_rate || 16000} Hz, ${res.audio_channels || 1} Ch, mono PCM)`,
          status: res.is_silent ? 'warning' : 'success',
        },
        {
          id: `log_asr_${Date.now()}`,
          timestamp: nowTime,
          stage: 'Speech Transcription',
          message: res.is_silent
            ? 'ASR bypassed (silent demonstration recording). Visual evidence primary.'
            : 'ASR model loading (faster-whisper base, Japanese detection 0.9839)...',
          status: res.is_silent ? 'warning' : 'processing',
        },
      ];

      setDataset((prev) => ({
        ...prev,
        video: {
          filename: res.filename,
          size_bytes: res.size_bytes,
          duration_sec: res.duration_sec,
          width: res.width,
          height: res.height,
          codec: res.codec,
          fps: res.fps,
          container_format: res.container_format,
          audio_codec: res.audio_codec,
          sample_rate: res.sample_rate,
          audio_channels: res.audio_channels,
        },
        stages: prev.stages.map((stage) => {
          if (stage.key === 'video_intake') {
            return { ...stage, status: 'completed', elapsed_sec: 1.2 };
          }
          if (stage.key === 'audio_extraction') {
            return {
              ...stage,
              status: res.is_silent ? 'skipped' : 'completed',
              elapsed_sec: res.extraction_time_sec || 3.4,
            };
          }
          if (stage.key === 'speech_transcription') {
            return {
              ...stage,
              status: res.is_silent ? 'skipped' : 'processing',
              elapsed_sec: 15.0,
            };
          }
          return stage;
        }),
        logs: [...prev.logs, ...newLogs],
      }));

      setVideoStreamUrl(sopApi.getStreamUrl(filename));
      setVideoCurrentTime(0);
      setIsPlaying(false);
    } finally {
      setIsIngesting(false);
    }
  };

  /**
   * Upload video file and execute real backend Video Ingestion and Audio Extraction
   */
  const uploadVideoFile = async (file: File) => {
    // Instantly bind local Blob URL so the video player displays the uploaded file immediately
    const localBlobUrl = URL.createObjectURL(file);
    setVideoStreamUrl(localBlobUrl);
    setVideoCurrentTime(0);
    setIsPlaying(false);
    setIsIngesting(true);
    try {
      const res = await sopApi.uploadAndIngestVideo(file);
      const nowTime = new Date().toTimeString().slice(0, 8);

      const newLogs: ProcessingLogEntry[] = [
        {
          id: `log_up_intake_${Date.now()}`,
          timestamp: nowTime,
          stage: 'Video Intake',
          message: `Uploaded file validated: ${res.width}x${res.height} @ ${res.fps} fps (${res.codec.toUpperCase()}), ${(res.size_bytes / (1024 * 1024)).toFixed(2)} MB`,
          status: 'success',
        },
        {
          id: `log_up_audio_${Date.now()}`,
          timestamp: nowTime,
          stage: 'Audio Extraction',
          message: res.is_silent
            ? 'No audio stream detected. Audio extraction skipped.'
            : `Audio extracted (${res.sample_rate || 16000} Hz, ${res.audio_channels || 1} Ch, mono PCM)`,
          status: res.is_silent ? 'warning' : 'success',
        },
        {
          id: `log_up_asr_${Date.now()}`,
          timestamp: nowTime,
          stage: 'Speech Transcription',
          message: res.is_silent
            ? 'ASR bypassed: silent demonstration.'
            : 'ASR model loading (faster-whisper base)...',
          status: res.is_silent ? 'warning' : 'processing',
        },
      ];

      setDataset((prev) => ({
        ...prev,
        video: {
          filename: res.filename,
          size_bytes: res.size_bytes,
          duration_sec: res.duration_sec,
          width: res.width,
          height: res.height,
          codec: res.codec,
          fps: res.fps,
          container_format: res.container_format,
          audio_codec: res.audio_codec,
          sample_rate: res.sample_rate,
          audio_channels: res.audio_channels,
        },
        stages: prev.stages.map((stage) => {
          if (stage.key === 'video_intake') {
            return { ...stage, status: 'completed', elapsed_sec: 1.5 };
          }
          if (stage.key === 'audio_extraction') {
            return {
              ...stage,
              status: res.is_silent ? 'skipped' : 'completed',
              elapsed_sec: res.extraction_time_sec || 2.8,
            };
          }
          if (stage.key === 'speech_transcription') {
            return {
              ...stage,
              status: res.is_silent ? 'skipped' : 'processing',
              elapsed_sec: 12.0,
            };
          }
          return stage;
        }),
        logs: [...prev.logs, ...newLogs],
      }));

      setVideoStreamUrl((prev) => (prev.startsWith('blob:') ? prev : sopApi.getStreamUrl(file.name)));
      setVideoCurrentTime(0);
      setIsPlaying(false);
    } finally {
      setIsIngesting(false);
    }
  };

  const totalStepsCount = dataset.steps.length;
  const approvedCount = dataset.steps.filter((s) => s.status === 'approved').length;
  const allStepsApproved = totalStepsCount > 0 && approvedCount === totalStepsCount;
  const hasUnresolvedConflicts = dataset.conflicts.some((c) => !c.resolved);

  const seekTo = (timeSec: number) => {
    setVideoCurrentTime(timeSec);
  };

  const handleResolveConflict = async (
    conflictId: string,
    resolution: 'video' | 'manual' | 'merge' | 'escalate',
    comment: string
  ) => {
    await sopApi.resolveConflict(conflictId, resolution, comment);

    setDataset((prev) => {
      const updatedConflicts = prev.conflicts.map((c) => {
        if (c.id === conflictId) {
          return {
            ...c,
            resolved: true,
            resolution,
            resolution_comment: comment,
            resolved_at: new Date().toISOString().replace('T', ' ').slice(0, 19),
          };
        }
        return c;
      });

      const matchingConflict = prev.conflicts.find((c) => c.id === conflictId);
      let updatedSteps = prev.steps;
      if (matchingConflict) {
        updatedSteps = prev.steps.map((s) => {
          if (s.id === matchingConflict.step_id && s.status === 'needs_review') {
            return {
              ...s,
              status: 'approved',
              reviewer_notes: `Conflict resolved via: ${resolution}. Note: ${comment}`,
            };
          }
          return s;
        });
      }

      return {
        ...prev,
        conflicts: updatedConflicts,
        steps: updatedSteps,
      };
    });
  };

  const handleUpdateStepReview = async (
    stepId: string,
    status: StepReviewStatus,
    notes?: string
  ) => {
    await sopApi.updateStepReview(stepId, status, notes);

    setDataset((prev) => {
      const updatedSteps = prev.steps.map((s) => {
        if (s.id === stepId) {
          return {
            ...s,
            status,
            reviewer_notes: notes !== undefined ? notes : s.reviewer_notes,
          };
        }
        return s;
      });

      const allNowApproved = updatedSteps.every((s) => s.status === 'approved');

      return {
        ...prev,
        steps: updatedSteps,
        document: {
          ...prev.document,
          all_approved: allNowApproved,
          approved_by: allNowApproved ? 'Engineering Validation Team' : null,
          approved_date: allNowApproved ? new Date().toISOString().slice(0, 10) : null,
        },
      };
    });
  };

  return (
    <WorkflowContext.Provider
      value={{
        currentStage,
        setCurrentStage,
        activeDatasetType,
        switchDataset,
        video: dataset.video,
        videoStreamUrl,
        fixtures,
        isIngesting,
        ingestFixtureVideo,
        uploadVideoFile,
        pipelineStages: dataset.stages,
        logs: dataset.logs,
        steps: dataset.steps,
        conflicts: dataset.conflicts,
        document: dataset.document,
        selectedStepId,
        setSelectedStepId,
        videoCurrentTime,
        setVideoCurrentTime,
        isPlaying,
        setIsPlaying,
        playbackRate,
        setPlaybackRate,
        seekTo,
        resolveConflict: handleResolveConflict,
        updateStepReview: handleUpdateStepReview,
        allStepsApproved,
        approvedCount,
        totalStepsCount,
        hasUnresolvedConflicts,
      }}
    >
      {children}
    </WorkflowContext.Provider>
  );
};

// eslint-disable-next-line react-refresh/only-export-components
export const useSopWorkflow = (): WorkflowContextType => {
  const context = useContext(WorkflowContext);
  if (!context) {
    throw new Error('useSopWorkflow must be used within a WorkflowProvider');
  }
  return context;
};
