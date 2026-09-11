"""
app/audio/exceptions.py — Typed Exception Hierarchy for Audio Extraction & ASR

Defines fine-grained exceptions for audio extraction, resampling, format validation,
and automatic speech recognition (ASR) while preserving compatibility with base
media processing exception hierarchies.
"""

from __future__ import annotations

from app.video.exceptions import VideoProcessingError


class AudioProcessingError(VideoProcessingError):
    """Base exception for all audio extraction, resampling, and ASR failures."""


class AudioExtractionError(AudioProcessingError):
    """Raised when audio extraction CLI (FFmpeg) or demuxing fails."""


class AudioExtractionTimeoutError(AudioExtractionError):
    """Raised when audio extraction subprocess execution times out."""


class NoAudioStreamError(AudioProcessingError):
    """Raised when a media file contains no readable audio stream."""


class CorruptAudioStreamError(AudioProcessingError):
    """Raised when the audio bitstream is corrupt, truncated, or unreadable."""


class ASRModelLoadError(AudioProcessingError):
    """Raised when speech recognition model fails to load, initialize, or allocate."""


class ASRTranscriptionError(AudioProcessingError):
    """Raised when speech-to-text transcription fails."""


class DurationSyncMismatchError(AudioProcessingError):
    """Raised when extracted audio duration deviates from source video duration by more than the tolerance."""

