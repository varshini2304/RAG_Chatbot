"""
video_loader.py — In-Memory Video Stream Demuxing & Validation Engine
Step 2: Video Stream Ingestion & Metadata Validation

Provides memory-efficient container demuxing, metadata extraction,
and frame decoding using PyAV (C-bindings to FFmpeg) with fallback ffprobe
validation and typed error handling.
"""

from __future__ import annotations

import io
import json
import logging
import subprocess
from collections.abc import Generator
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO, ClassVar, Self

import av
import numpy as np

from app.config import settings
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

logger = logging.getLogger("video_loader")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


@dataclass
class VideoStreamInfo:
    """Metadata descriptor for a single video stream."""

    index: int
    codec_name: str
    width: int
    height: int
    fps: float
    average_fps: float
    duration_sec: float
    is_vfr: bool
    num_frames: int | None = None
    time_base: str = ""
    pix_fmt: str = ""


@dataclass
class AudioStreamInfo:
    """Metadata descriptor for a single audio stream."""

    index: int
    codec_name: str
    sample_rate: int
    channels: int
    layout: str
    duration_sec: float


@dataclass
class ContainerMetadata:
    """Container-level metadata descriptor."""

    format_name: str
    duration_sec: float
    bit_rate: int | None
    size_bytes: int
    video_streams: list[VideoStreamInfo] = field(default_factory=list)
    audio_streams: list[AudioStreamInfo] = field(default_factory=list)
    is_vfr: bool = False

    @property
    def primary_video_stream(self) -> VideoStreamInfo | None:
        """Returns the primary video stream if available."""
        return self.video_streams[0] if self.video_streams else None

    @property
    def primary_audio_stream(self) -> AudioStreamInfo | None:
        """Returns the primary audio stream if available."""
        return self.audio_streams[0] if self.audio_streams else None


@dataclass
class DecodedFrame:
    """Representation of an uncompressed RGB video frame."""

    frame_index: int
    timestamp_sec: float
    width: int
    height: int
    format: str
    data: np.ndarray  # (H, W, 3) RGB uint8 numpy array


@dataclass
class FFprobeMetadata:
    """Structured container and stream metadata extracted via ffprobe ground truth."""

    codec: str
    width: int
    height: int
    fps: float
    duration_sec: float
    container_format: str
    bit_rate: int | None = None
    size_bytes: int = 0
    audio_codec: str | None = None
    audio_channels: int | None = None
    sample_rate: int | None = None
    raw_streams: list[dict] = field(default_factory=list)
    raw_format: dict = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Outcome descriptor for video validation gatekeeper check."""

    is_valid: bool
    rejection_reason: str | None = None
    metadata: FFprobeMetadata | None = None

    @property
    def passed(self) -> bool:
        return self.is_valid


class VideoLoader:
    """
    In-memory video stream demuxer and frame extractor using PyAV.

    Supports:
      - Local filesystem paths (str, Path)
      - In-memory binary streams (bytes, io.BytesIO)
      - Standard containers (MP4, WebM, OGV, MOV, MKV)
      - Variable Frame Rate (VFR) streams
      - Pre-demuxing validation gatekeeper checks
    """

    # Maximum file size ceiling pulled from authoritative settings
    DEFAULT_MAX_SIZE_BYTES: ClassVar[int] = settings.video_max_size_bytes

    def __init__(
        self,
        source: str | Path | bytes | BinaryIO,
        max_size_bytes: int | None = None,
        require_video_stream: bool = False,
        validate_with_gatekeeper: bool = False,
        gatekeeper: ValidationGatekeeper | None = None,
    ):
        self._source = source
        self._max_size_bytes = (
            max_size_bytes if max_size_bytes is not None else settings.video_max_size_bytes
        )
        self._require_video_stream = require_video_stream
        self._validate_with_gatekeeper = validate_with_gatekeeper
        self._gatekeeper = gatekeeper
        self._container: av.container.InputContainer | None = None
        self._metadata: ContainerMetadata | None = None
        self._ffprobe_metadata: FFprobeMetadata | None = None
        self._stream_buffer: io.BytesIO | None = None

    def __enter__(self) -> Self:
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def open(self) -> ContainerMetadata:
        """
        Opens and demuxes the media container in-memory.

        Returns:
            ContainerMetadata object with stream details.

        Raises:
            InvalidInputError: If source is missing, unreadable, or empty.
            FileSizeLimitExceededError: If file size exceeds configured threshold.
            UnsupportedContainerError: If container format is unknown.
            UnsupportedCodecError: If validate_with_gatekeeper is True and codec is unsupported.
            CorruptMediaError: If container header or bitstream is corrupt.
            NoVideoStreamError: If require_video_stream is True and no video stream exists.
        """
        if self._container is not None and self._metadata is not None:
            return self._metadata

        # Pre-processing Gatekeeper Validation if requested
        if self._validate_with_gatekeeper and isinstance(self._source, (str, Path)):
            gk = self._gatekeeper or ValidationGatekeeper(max_size_bytes=self._max_size_bytes)
            v_res = gk.validate(self._source, strict=True)
            self._ffprobe_metadata = v_res.metadata

        file_size = 0
        input_target: str | BinaryIO

        if isinstance(self._source, (str, Path)):
            path = Path(self._source)
            if not path.exists():
                raise InvalidInputError(f"Input video file does not exist: {path.name}")
            if not path.is_file():
                raise InvalidInputError(f"Input target is not a regular file: {path.name}")

            file_size = path.stat().st_size
            if file_size == 0:
                raise InvalidInputError(f"Input video file is empty (0 bytes): {path.name}")
            if file_size > self._max_size_bytes:
                raise FileSizeLimitExceededError(
                    f"Video file size ({file_size} bytes) exceeds maximum configured limit "
                    f"({self._max_size_bytes} bytes)."
                )
            input_target = str(path)

        elif isinstance(self._source, bytes):
            file_size = len(self._source)
            if file_size == 0:
                raise InvalidInputError("Input bytes buffer is empty (0 bytes).")
            if file_size > self._max_size_bytes:
                raise FileSizeLimitExceededError(
                    f"In-memory video buffer ({file_size} bytes) exceeds maximum threshold."
                )
            self._stream_buffer = io.BytesIO(self._source)
            input_target = self._stream_buffer

        elif hasattr(self._source, "read"):
            self._stream_buffer = io.BytesIO(self._source.read())
            file_size = self._stream_buffer.getbuffer().nbytes
            if file_size == 0:
                raise InvalidInputError("Provided binary stream is empty (0 bytes).")
            input_target = self._stream_buffer

        else:
            raise InvalidInputError(
                f"Unsupported source type: {type(self._source).__name__}. "
                "Expected str, Path, bytes, or BinaryIO."
            )

        try:
            self._container = av.open(input_target, mode="r")
        except av.InvalidDataError as e:
            raise CorruptMediaError(f"Media container is corrupt or truncated: {e}") from e
        except av.FFmpegError as e:
            err_msg = str(e)
            if "Invalid data found" in err_msg or "end of file" in err_msg:
                raise CorruptMediaError(f"Bitstream parsing failure: {err_msg}") from e
            raise UnsupportedContainerError(f"Failed to open media container: {err_msg}") from e
        except Exception as e:
            raise CorruptMediaError(f"Unexpected container demuxing error: {e}") from e

        self._metadata = self._extract_metadata(file_size)

        if self._require_video_stream and not self._metadata.video_streams:
            self.close()
            raise NoVideoStreamError(
                f"Media source contains no video streams (found {len(self._metadata.audio_streams)} audio stream(s))."
            )

        return self._metadata

    def _extract_metadata(self, file_size: int) -> ContainerMetadata:
        """Helper to parse container and stream structures."""
        assert self._container is not None

        format_name = self._container.format.name if self._container.format else "unknown"
        raw_dur = self._container.duration
        duration_sec = float(raw_dur or 0) / 1_000_000 if raw_dur else 0.0
        bit_rate = self._container.bit_rate

        video_streams: list[VideoStreamInfo] = []
        is_container_vfr = False

        for v_stream in self._container.streams.video:
            avg_rate = float(v_stream.average_rate or 0)
            base_rate = float(v_stream.base_rate or 0)

            stream_vfr = False
            if avg_rate > 0 and base_rate > 0 and abs(avg_rate - base_rate) > 0.05:
                stream_vfr = True

            if stream_vfr:
                is_container_vfr = True

            v_dur = (
                float(v_stream.duration or 0) * float(v_stream.time_base or 0)
                if v_stream.duration
                else duration_sec
            )

            v_info = VideoStreamInfo(
                index=v_stream.index,
                codec_name=v_stream.codec_context.name if v_stream.codec_context else "unknown",
                width=v_stream.codec_context.width if v_stream.codec_context else 0,
                height=v_stream.codec_context.height if v_stream.codec_context else 0,
                fps=avg_rate if avg_rate > 0 else base_rate,
                average_fps=avg_rate,
                duration_sec=round(v_dur, 3),
                is_vfr=stream_vfr,
                num_frames=v_stream.frames if v_stream.frames > 0 else None,
                time_base=str(v_stream.time_base),
                pix_fmt=(v_stream.codec_context.pix_fmt or "") if v_stream.codec_context else "",
            )
            video_streams.append(v_info)

        audio_streams: list[AudioStreamInfo] = []
        for a_stream in self._container.streams.audio:
            a_dur = (
                float(a_stream.duration or 0) * float(a_stream.time_base or 0)
                if a_stream.duration
                else duration_sec
            )
            a_info = AudioStreamInfo(
                index=a_stream.index,
                codec_name=a_stream.codec_context.name if a_stream.codec_context else "unknown",
                sample_rate=a_stream.codec_context.sample_rate if a_stream.codec_context else 0,
                channels=a_stream.codec_context.channels if a_stream.codec_context else 0,
                layout=(
                    a_stream.codec_context.layout.name
                    if (a_stream.codec_context and a_stream.codec_context.layout)
                    else "unknown"
                ),
                duration_sec=round(a_dur, 3),
            )
            audio_streams.append(a_info)

        return ContainerMetadata(
            format_name=format_name,
            duration_sec=round(duration_sec, 3),
            bit_rate=bit_rate,
            size_bytes=file_size,
            video_streams=video_streams,
            audio_streams=audio_streams,
            is_vfr=is_container_vfr,
        )

    def get_metadata(self) -> ContainerMetadata:
        """Returns container metadata, opening if necessary."""
        if self._metadata is None:
            return self.open()
        return self._metadata

    @property
    def ffprobe_metadata(self) -> FFprobeMetadata | None:
        """Returns ffprobe metadata if gatekeeper validation was executed."""
        return self._ffprobe_metadata

    def decode_first_frame(self) -> DecodedFrame:
        """
        Decodes and returns the initial video keyframe as an uncompressed RGB24 numpy array.

        Returns:
            DecodedFrame object.

        Raises:
            NoVideoStreamError: If no video stream exists.
            DecodeError: If frame decoding fails.
        """
        if self._container is None:
            self.open()
        assert self._container is not None

        if not self._container.streams.video:
            raise NoVideoStreamError("Media container contains no video stream.")

        try:
            self._container.seek(0)
            for frame in self._container.decode(video=0):
                rgb_img = frame.to_ndarray(format="rgb24")
                pts_sec = float(frame.pts or 0) * float(frame.time_base or 0)
                return DecodedFrame(
                    frame_index=frame.index if hasattr(frame, "index") else 0,
                    timestamp_sec=round(pts_sec, 3),
                    width=frame.width,
                    height=frame.height,
                    format="RGB24",
                    data=rgb_img,
                )
        except Exception as e:
            raise DecodeError(f"Failed to decode initial video frame: {e}") from e

        raise DecodeError("No frames yielded from the video stream.")

    def decode_frames(
        self,
        max_frames: int | None = None,
        stride: int = 1,
    ) -> Generator[DecodedFrame, None, None]:
        """
        Generator yielding decoded video frames lazily.

        Args:
            max_frames: Maximum number of frames to yield.
            stride: Sample every Nth frame.

        Yields:
            DecodedFrame instances.
        """
        if self._container is None:
            self.open()
        assert self._container is not None

        if not self._container.streams.video:
            raise NoVideoStreamError("Media container contains no video stream.")

        count = 0
        yielded = 0
        try:
            self._container.seek(0)
            for frame in self._container.decode(video=0):
                if count % stride == 0:
                    rgb_img = frame.to_ndarray(format="rgb24")
                    pts_sec = float(frame.pts or 0) * float(frame.time_base or 0)
                    yield DecodedFrame(
                        frame_index=count,
                        timestamp_sec=round(pts_sec, 3),
                        width=frame.width,
                        height=frame.height,
                        format="RGB24",
                        data=rgb_img,
                    )
                    yielded += 1
                    if max_frames and yielded >= max_frames:
                        break
                count += 1
        except Exception as e:
            raise DecodeError(f"Stream decode error encountered at frame {count}: {e}") from e

    def close(self) -> None:
        """Closes container handles and releases in-memory buffer."""
        if self._container is not None:
            try:
                self._container.close()
            except (av.FFmpegError, OSError) as e:
                logger.debug("Error closing container: %s", e)
            self._container = None
        if self._stream_buffer is not None:
            try:
                self._stream_buffer.close()
            except (OSError, ValueError) as e:
                logger.debug("Error closing stream buffer: %s", e)
            self._stream_buffer = None


def extract_metadata_ffprobe(video_path: str | Path, timeout_sec: int = 30) -> FFprobeMetadata:
    """
    Executes ffprobe CLI as metadata ground truth, extracting video stream codec,
    dimensions, frame rate, duration, and container format.

    Args:
        video_path: Path to target media file.
        timeout_sec: Maximum execution timeout in seconds.

    Returns:
        FFprobeMetadata object with extracted fields.

    Raises:
        InvalidInputError: If file is missing, empty, or not a regular file.
        CorruptMediaError: If ffprobe returns non-zero code or outputs invalid JSON.
        NoVideoStreamError: If container contains no video stream.
        VideoProcessingError: If ffprobe binary is missing or times out.
    """
    path = Path(video_path)
    if not path.exists():
        raise InvalidInputError(f"Target video file does not exist: {path.name}")
    if not path.is_file():
        raise InvalidInputError(f"Target path is not a regular file: {path.name}")
    if path.stat().st_size == 0:
        raise InvalidInputError(f"Target video file is empty (0 bytes): {path.name}")

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_streams",
        "-show_format",
        str(path),
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
    except FileNotFoundError:
        raise FFprobeExecutionError("ffprobe executable not found in system PATH.")
    except subprocess.TimeoutExpired:
        raise FFprobeTimeoutError(f"ffprobe execution timed out after {timeout_sec}s.")

    if proc.returncode != 0:
        err_msg = proc.stderr.strip() or f"Exit code {proc.returncode}"
        raise CorruptMediaError(f"ffprobe metadata extraction failed: {err_msg}")

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise CorruptMediaError(f"Failed to parse ffprobe JSON output: {e}") from e

    streams = data.get("streams", [])
    format_data = data.get("format", {})

    vid = next((s for s in streams if s.get("codec_type") == "video"), None)
    if vid is None:
        raise NoVideoStreamError(f"No video stream detected by ffprobe in '{path.name}'.")

    aud = next((s for s in streams if s.get("codec_type") == "audio"), None)

    # Frame rate calculation (r_frame_rate preferred, fallback avg_frame_rate)
    fps = 0.0
    fps_str = vid.get("r_frame_rate") or vid.get("avg_frame_rate") or "0/1"
    try:
        parts = fps_str.split("/")
        if len(parts) == 2 and int(parts[1]) != 0:
            fps = round(int(parts[0]) / int(parts[1]), 3)
    except (ValueError, ZeroDivisionError):
        fps = 0.0

    # Duration calculation (container duration preferred, fallback stream duration)
    raw_dur = format_data.get("duration") or vid.get("duration") or 0.0
    try:
        duration_sec = round(float(raw_dur), 3)
    except (ValueError, TypeError):
        duration_sec = 0.0

    # Bitrate calculation
    raw_bitrate = format_data.get("bit_rate") or vid.get("bit_rate")
    try:
        bit_rate = int(raw_bitrate) if raw_bitrate else None
    except (ValueError, TypeError):
        bit_rate = None

    # Size calculation
    raw_size = format_data.get("size")
    try:
        size_bytes = int(raw_size) if raw_size else path.stat().st_size
    except (ValueError, TypeError):
        size_bytes = path.stat().st_size

    # Audio details
    audio_codec = aud.get("codec_name") if aud else None
    audio_channels = int(aud.get("channels", 0)) if (aud and aud.get("channels")) else None
    sample_rate = int(aud.get("sample_rate", 0)) if (aud and aud.get("sample_rate")) else None

    return FFprobeMetadata(
        codec=vid.get("codec_name", "unknown"),
        width=int(vid.get("width", 0)),
        height=int(vid.get("height", 0)),
        fps=fps,
        duration_sec=duration_sec,
        container_format=format_data.get("format_name", "unknown"),
        bit_rate=bit_rate,
        size_bytes=size_bytes,
        audio_codec=audio_codec,
        audio_channels=audio_channels,
        sample_rate=sample_rate,
        raw_streams=streams,
        raw_format=format_data,
    )


class ValidationGatekeeper:
    """
    Pre-processing validation gatekeeper for incoming video media.

    Enforces the pipeline:
      Input Video -> Basic Input Validation -> ffprobe Metadata Inspection -> Metadata Validation -> PASS / FAIL

    Blocks downstream processing if media is missing, corrupt, non-video, or uses unsupported codecs/formats.
    """

    DEFAULT_SUPPORTED_CODECS: ClassVar[set[str]] = {"h264", "vp9"}
    DEFAULT_SUPPORTED_FORMATS: ClassVar[set[str]] = {
        "mp4",
        "mov",
        "m4a",
        "3gp",
        "3g2",
        "mj2",
        "webm",
        "matroska",
        "matroska,webm",
        "mov,mp4,m4a,3gp,3g2,mj2",
    }
    DEFAULT_MAX_SIZE_BYTES: ClassVar[int] = settings.video_max_size_bytes
    DEFAULT_MAX_DURATION_SEC: ClassVar[float] = settings.video_max_duration_sec

    def __init__(
        self,
        supported_codecs: set[str] | None = None,
        supported_formats: set[str] | None = None,
        max_size_bytes: int | None = None,
        max_duration_sec: float | None = None,
    ):
        configured_codecs = (
            set(settings.video_supported_codecs)
            if settings.video_supported_codecs
            else self.DEFAULT_SUPPORTED_CODECS
        )
        configured_formats = (
            set(settings.video_supported_formats)
            if settings.video_supported_formats
            else self.DEFAULT_SUPPORTED_FORMATS
        )
        self.supported_codecs = {
            c.lower() for c in (supported_codecs if supported_codecs is not None else configured_codecs)
        }
        self.supported_formats = {
            f.lower() for f in (supported_formats if supported_formats is not None else configured_formats)
        }
        self.max_size_bytes = (
            max_size_bytes if max_size_bytes is not None else settings.video_max_size_bytes
        )
        self.max_duration_sec = (
            max_duration_sec if max_duration_sec is not None else settings.video_max_duration_sec
        )

    def validate(
        self,
        video_path: str | Path,
        strict: bool = False,
    ) -> ValidationResult:
        """
        Executes gatekeeper validation against target video.

        Args:
            video_path: Path to target media file.
            strict: If True, raises typed exceptions instead of returning failed ValidationResult.

        Returns:
            ValidationResult with boolean status, user-safe rejection message, and metadata.

        Raises:
            InvalidInputError: If strict=True and basic input validation fails.
            FileSizeLimitExceededError: If strict=True and file size exceeds maximum configured limit.
            CorruptMediaError: If strict=True and media is corrupt/unreadable.
            NoVideoStreamError: If strict=True and no video stream exists.
            UnsupportedCodecError: If strict=True and video codec is not supported.
            UnsupportedContainerError: If strict=True and container format is not supported.
            MetadataValidationError: If strict=True and dimensions/duration/fps are invalid.
            VideoDurationLimitExceededError: If strict=True and duration exceeds maximum limit.
        """
        path = Path(video_path)

        # 1. Basic Input Validation
        if not path.exists():
            reason = f"Video file not found: {path.name}"
            if strict:
                raise InvalidInputError(reason)
            return ValidationResult(is_valid=False, rejection_reason=reason)

        if not path.is_file():
            reason = f"Target is not a valid file: {path.name}"
            if strict:
                raise InvalidInputError(reason)
            return ValidationResult(is_valid=False, rejection_reason=reason)

        file_size = path.stat().st_size
        if file_size == 0:
            reason = f"Video file is empty (0 bytes): {path.name}"
            if strict:
                raise InvalidInputError(reason)
            return ValidationResult(is_valid=False, rejection_reason=reason)

        if file_size > self.max_size_bytes:
            reason = (
                f"Video file size ({file_size} bytes) exceeds maximum limit "
                f"({self.max_size_bytes} bytes)."
            )
            if strict:
                raise FileSizeLimitExceededError(reason)
            return ValidationResult(is_valid=False, rejection_reason=reason)

        # 2. ffprobe Metadata Inspection
        try:
            metadata = extract_metadata_ffprobe(path)
        except InvalidInputError as e:
            if strict:
                raise
            return ValidationResult(is_valid=False, rejection_reason=str(e))
        except NoVideoStreamError as e:
            reason = f"Media container has no video stream: {path.name}"
            if strict:
                raise NoVideoStreamError(reason) from e
            return ValidationResult(is_valid=False, rejection_reason=reason)
        except CorruptMediaError as e:
            reason = f"Corrupt or unreadable media container: {path.name}"
            if strict:
                raise CorruptMediaError(reason) from e
            return ValidationResult(is_valid=False, rejection_reason=reason)
        except VideoProcessingError:
            reason = f"Media inspection failed: {path.name}"
            if strict:
                raise
            return ValidationResult(is_valid=False, rejection_reason=reason)

        # 3. Metadata Validation
        # Check Codec
        if metadata.codec.lower() not in self.supported_codecs:
            allowed = ", ".join(sorted(self.supported_codecs))
            reason = f"Unsupported video codec '{metadata.codec}'. Supported codecs are: {allowed}."
            if strict:
                raise UnsupportedCodecError(reason)
            return ValidationResult(is_valid=False, rejection_reason=reason, metadata=metadata)

        # Check Container Format
        fmt_parts = [p.strip().lower() for p in metadata.container_format.split(",")]
        is_fmt_supported = any(
            p in self.supported_formats for p in fmt_parts
        ) or metadata.container_format.lower() in self.supported_formats

        if not is_fmt_supported:
            allowed_fmts = ", ".join(sorted(self.supported_formats))
            reason = (
                f"Unsupported container format '{metadata.container_format}'. "
                f"Supported formats are: {allowed_fmts}."
            )
            if strict:
                raise UnsupportedContainerError(reason)
            return ValidationResult(is_valid=False, rejection_reason=reason, metadata=metadata)

        # Check Dimensions
        if metadata.width <= 0 or metadata.height <= 0:
            reason = f"Invalid video dimensions ({metadata.width}x{metadata.height}). Must be greater than 0."
            if strict:
                raise MetadataValidationError(reason)
            return ValidationResult(is_valid=False, rejection_reason=reason, metadata=metadata)

        # Check Duration
        if metadata.duration_sec <= 0.0:
            reason = f"Invalid video duration ({metadata.duration_sec}s). Must be greater than 0."
            if strict:
                raise MetadataValidationError(reason)
            return ValidationResult(is_valid=False, rejection_reason=reason, metadata=metadata)

        if metadata.duration_sec > self.max_duration_sec:
            reason = (
                f"Video duration ({metadata.duration_sec}s) exceeds maximum allowed limit "
                f"({self.max_duration_sec}s)."
            )
            if strict:
                raise VideoDurationLimitExceededError(reason)
            return ValidationResult(is_valid=False, rejection_reason=reason, metadata=metadata)

        # Check Frame Rate
        if metadata.fps <= 0.0:
            reason = f"Invalid video frame rate ({metadata.fps} fps). Must be greater than 0."
            if strict:
                raise MetadataValidationError(reason)
            return ValidationResult(is_valid=False, rejection_reason=reason, metadata=metadata)

        return ValidationResult(is_valid=True, metadata=metadata)


def validate_video_gatekeeper(
    video_path: str | Path,
    supported_codecs: set[str] | None = None,
    supported_formats: set[str] | None = None,
    max_size_bytes: int | None = None,
    max_duration_sec: float | None = None,
    strict: bool = False,
) -> ValidationResult:
    """
    Convenience wrapper executing ValidationGatekeeper against a video file.

    Args:
        video_path: Path to target media file.
        supported_codecs: Optional set of allowed codecs (defaults to config setting).
        supported_formats: Optional set of allowed container formats (defaults to config setting).
        max_size_bytes: Optional size threshold override in bytes (defaults to config setting).
        max_duration_sec: Optional duration threshold override in seconds (defaults to config setting).
        strict: If True, raises typed exceptions instead of returning failed result.

    Returns:
        ValidationResult with pass/fail and user-safe rejection reason.
    """
    gatekeeper = ValidationGatekeeper(
        supported_codecs=supported_codecs,
        supported_formats=supported_formats,
        max_size_bytes=max_size_bytes,
        max_duration_sec=max_duration_sec,
    )
    return gatekeeper.validate(video_path, strict=strict)


def probe_container_ffprobe(video_path: str | Path, timeout_sec: int = 30) -> dict:
    """
    External container verification wrapper using ffprobe CLI.

    Args:
        video_path: Path to target video.
        timeout_sec: Maximum execution timeout in seconds.

    Returns:
        Parsed JSON dictionary of streams and format.
    """
    path = Path(video_path)
    if not path.exists() or not path.is_file():
        raise InvalidInputError(f"Target video file does not exist: {path.name}")

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_streams",
        "-show_format",
        str(path),
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
    except FileNotFoundError:
        raise FFprobeExecutionError("ffprobe executable not found in system PATH.")
    except subprocess.TimeoutExpired:
        raise FFprobeTimeoutError(f"ffprobe execution timed out after {timeout_sec}s.")

    if proc.returncode != 0:
        err_msg = proc.stderr.strip() or f"Exit code {proc.returncode}"
        raise CorruptMediaError(f"ffprobe inspection failed: {err_msg}")

    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise CorruptMediaError(f"Failed to parse ffprobe JSON output: {e}") from e
