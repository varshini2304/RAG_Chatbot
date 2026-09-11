"""
app/audio — Audio Extraction, Speech Recognition (ASR) & Timestamp Synchronization Module
"""

from app.audio.alignment import (
    AlignmentAnnotation,
    AlignmentEvaluationReport,
    PhraseAlignmentResult,
    TimestampAlignmentEvaluator,
    WERCEREvaluator,
)
from app.audio.asr_engine import (
    ASREngine,
    ASRService,
    TranscriptionResult,
    TranscriptionSegment,
    WordTimestamp,
)
from app.audio.audio_extractor import (
    AudioExtractor,
    DurationSyncResult,
    ExtractedAudio,
    LoudnessMeasurement,
)
from app.audio.exceptions import (
    ASRModelLoadError,
    ASRTranscriptionError,
    AudioExtractionError,
    AudioExtractionTimeoutError,
    AudioProcessingError,
    CorruptAudioStreamError,
    DurationSyncMismatchError,
    NoAudioStreamError,
)

__all__ = [
    "ASREngine",
    "ASRModelLoadError",
    "ASRService",
    "ASRTranscriptionError",
    "AlignmentAnnotation",
    "AlignmentEvaluationReport",
    "AudioExtractionError",
    "AudioExtractionTimeoutError",
    "AudioExtractor",
    "AudioProcessingError",
    "CorruptAudioStreamError",
    "DurationSyncMismatchError",
    "DurationSyncResult",
    "ExtractedAudio",
    "LoudnessMeasurement",
    "NoAudioStreamError",
    "PhraseAlignmentResult",
    "TimestampAlignmentEvaluator",
    "TranscriptionResult",
    "TranscriptionSegment",
    "WERCEREvaluator",
    "WordTimestamp",
]

