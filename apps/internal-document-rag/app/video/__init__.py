"""
Video processing subpackage for Internal Document & Video RAG.
Step 2 & 3: Video Stream Ingestion, Metadata Validation & Pipeline Integration
"""

from app.video.exceptions import (
    CorruptMediaError,
    DecodeError,
    FFprobeExecutionError,
    FFprobeTimeoutError,
    FileSizeLimitExceededError,
    InvalidInputError,
    MetadataValidationError,
    NoVideoStreamError,
    UnsupportedCodecError,
    UnsupportedContainerError,
    VideoDurationLimitExceededError,
    VideoProcessingError,
)
from app.video.video_loader import (
    AudioStreamInfo,
    ContainerMetadata,
    DecodedFrame,
    FFprobeMetadata,
    ValidationGatekeeper,
    ValidationResult,
    VideoLoader,
    VideoStreamInfo,
    extract_metadata_ffprobe,
    probe_container_ffprobe,
    validate_video_gatekeeper,
)

__all__ = [
    "AudioStreamInfo",
    "ContainerMetadata",
    "CorruptMediaError",
    "DecodeError",
    "DecodedFrame",
    "FFprobeExecutionError",
    "FFprobeMetadata",
    "FFprobeTimeoutError",
    "FileSizeLimitExceededError",
    "InvalidInputError",
    "MetadataValidationError",
    "NoVideoStreamError",
    "UnsupportedCodecError",
    "UnsupportedContainerError",
    "ValidationGatekeeper",
    "ValidationResult",
    "VideoDurationLimitExceededError",
    "VideoLoader",
    "VideoProcessingError",
    "VideoStreamInfo",
    "extract_metadata_ffprobe",
    "probe_container_ffprobe",
    "validate_video_gatekeeper",
]
