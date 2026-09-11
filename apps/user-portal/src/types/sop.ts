/**
 * Domain types for RAG SOP — Manufacturing Knowledge System
 * Grounded in FastAPI backend contracts (FFprobeMetadata, ASR transcription, etc.)
 */

export interface VideoMetadata {
  filename: string;
  size_bytes: number;
  duration_sec: number;
  width: number;
  height: number;
  codec: string;
  fps: number;
  container_format: string;
  audio_codec: string | null; // null indicates silent video
  sample_rate: number | null;
  audio_channels: number | null;
}

export type PipelineStageKey =
  | 'video_intake'
  | 'audio_extraction'
  | 'speech_transcription'
  | 'step_detection'
  | 'translation';

export type StageStatus =
  | 'pending'
  | 'processing'
  | 'completed'
  | 'skipped'
  | 'failed'
  | 'unavailable';

export interface PipelineStageInfo {
  key: PipelineStageKey;
  label: string;
  status: StageStatus;
  description: string;
  elapsed_sec?: number;
}

export interface ProcessingLogEntry {
  id: string;
  timestamp: string;
  stage: string;
  message: string;
  status: 'success' | 'processing' | 'warning' | 'error';
}

export interface EvidenceItem {
  id: string;
  claim: string;
  source: 'video' | 'manual';
  timestamp_sec?: number;
  page_number?: number;
  keyframe_url?: string;
  observation: string;
}

export type StepReviewStatus = 'approved' | 'needs_review' | 'pending' | 'rejected';

export interface WorkStep {
  id: string;
  step_number: number;
  title: string;
  title_ja: string | null;
  description: string;
  description_ja: string | null;
  start_time: number;
  end_time: number;
  keyframe_url: string;
  status: StepReviewStatus;
  tools_required: string[] | null;
  ppe_required: string[] | null;
  safety_warnings: string[] | null;
  quality_checkpoints: string[] | null;
  expected_outcome: string | null;
  evidence: EvidenceItem[];
  reviewer_notes?: string;
}

export interface ConflictItem {
  id: string;
  step_id: string;
  step_number: number;
  step_title: string;
  video_evidence: {
    keyframe_url: string;
    timestamp_sec: number;
    observed_action: string;
    detected_tools: string[];
  };
  reference_manual: {
    document_name: string;
    page_number: number;
    relevant_instruction: string;
    required_tools: string[];
  };
  difference: string;
  resolution?: 'video' | 'manual' | 'merge' | 'escalate';
  resolution_comment?: string;
  resolved: boolean;
  resolved_at?: string;
}

export interface AuditEvent {
  id: string;
  timestamp: string;
  actor: string;
  action: string;
  stage: string;
  status: 'completed' | 'skipped' | 'verified' | 'resolved' | 'approved' | 'pending';
  details?: string;
}

export interface SOPDocument {
  id: string;
  title: string;
  title_ja: string | null;
  version: string;
  approved_by: string | null;
  approved_date: string | null;
  all_approved: boolean;
  steps: WorkStep[];
  audit_trail: AuditEvent[];
}

export type WorkflowStageNumber = 1 | 2 | 3 | 4 | 5 | 6;

export interface WorkflowState {
  currentStage: WorkflowStageNumber;
  video: VideoMetadata | null;
  pipelineStages: PipelineStageInfo[];
  logs: ProcessingLogEntry[];
  steps: WorkStep[];
  conflicts: ConflictItem[];
  sopDocument: SOPDocument | null;
  selectedStepId: string | null;
  videoCurrentTime: number;
  isPlaying: boolean;
}
