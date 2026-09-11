"""
exceptions.py — Custom Typed Exceptions for Video Processing Pipeline
Part of Step 2: Video Stream Ingestion & Metadata Validation
"""

class VideoProcessingError(Exception):
    """Base exception for all video processing errors."""


class InvalidInputError(VideoProcessingError):
    """Raised when the input path or stream is missing, unreadable, empty, or exceeds size limits."""


class UnsupportedContainerError(VideoProcessingError):
    """Raised when the media container or codec is unknown or unsupported."""


class CorruptMediaError(VideoProcessingError):
    """Raised when the container header or bitstream is corrupt/truncated."""


class NoVideoStreamError(VideoProcessingError):
    """Raised when the container contains valid streams but no video stream."""


class DecodeError(VideoProcessingError):
    """Raised when a video frame fails to decode properly."""


class UnsupportedCodecError(UnsupportedContainerError):
    """Raised when the video stream codec is not supported by the ingestion pipeline."""


class MetadataValidationError(VideoProcessingError):
    """Raised when extracted metadata fails gatekeeper validation rules."""


class FileSizeLimitExceededError(InvalidInputError):
    """Raised when the input video file size exceeds the configured maximum threshold."""


class VideoDurationLimitExceededError(MetadataValidationError):
    """Raised when the video duration exceeds the configured maximum threshold."""


class FFprobeExecutionError(VideoProcessingError):
    """Raised when ffprobe execution fails, encounters an error, or returns non-zero exit code."""


class FFprobeTimeoutError(FFprobeExecutionError):
    """Raised when ffprobe execution times out."""

