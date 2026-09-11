"""
app/audio/audio_extractor.py — FFmpeg Audio Extraction, Resampling & Duration Synchronization

Implements canonical FFmpeg CLI extraction to 16 kHz mono 16-bit PCM (pcm_s16le).
Supports EBU R128 loudness normalization and configurable silence trimming.
Performs source-duration synchronization check against source video FFprobe duration
using the authoritative Row 03 tolerance of +/-2.0 seconds.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
import tempfile
import time
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

from app.audio.exceptions import (
    AudioExtractionError,
    AudioExtractionTimeoutError,
    CorruptAudioStreamError,
    DurationSyncMismatchError,
    NoAudioStreamError,
)
from app.config import settings
from app.video.exceptions import (
    CorruptMediaError,
    VideoProcessingError,
)
from app.video.video_loader import (
    ValidationGatekeeper,
    extract_metadata_ffprobe,
)

logger = logging.getLogger("audio_extractor")


@dataclass(frozen=True)
class LoudnessMeasurement:
    """
    Parsed EBU R128 loudness metrics from FFmpeg loudnorm filter diagnostics.

    Note: The default target values (I=-23 LUFS, LRA=7 LU, TP=-2 dBTP) represent
    the broadcast standard implementation baseline, not historical R&D-validated values.
    """

    input_i: float
    input_tp: float
    input_lra: float
    input_thresh: float
    output_i: float
    output_tp: float
    output_lra: float
    output_thresh: float
    normalization_type: str
    target_offset: float
    raw_json: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LoudnessMeasurement:
        return cls(
            input_i=float(data.get("input_i", 0.0)),
            input_tp=float(data.get("input_tp", 0.0)),
            input_lra=float(data.get("input_lra", 0.0)),
            input_thresh=float(data.get("input_thresh", 0.0)),
            output_i=float(data.get("output_i", 0.0)),
            output_tp=float(data.get("output_tp", 0.0)),
            output_lra=float(data.get("output_lra", 0.0)),
            output_thresh=float(data.get("output_thresh", 0.0)),
            normalization_type=str(data.get("normalization_type", "dynamic")),
            target_offset=float(data.get("target_offset", 0.0)),
            raw_json=data,
        )


@dataclass(frozen=True)
class DurationSyncResult:
    """
    Encapsulates duration comparison between source video and extracted audio.

    Duration delta is calculated as:
        delta = audio_duration - source_video_duration
    and passes when abs(delta) <= tolerance_sec (authoritative Row 03 tolerance: +/-2.0s).
    """

    source_video_duration_sec: float
    audio_duration_sec: float
    duration_difference_sec: float
    tolerance_sec: float
    is_within_tolerance: bool


@dataclass(frozen=True)
class ExtractedAudio:
    """Encapsulates extracted and resampled PCM audio metadata, path, and validation metrics."""

    file_path: Path
    duration_sec: float
    raw_duration_sec: float
    sample_rate: int
    channels: int
    sample_width_bytes: int
    file_size_bytes: int
    num_frames: int
    extraction_time_sec: float
    loudness_measurement: LoudnessMeasurement | None = None
    duration_sync: DurationSyncResult | None = None
    trimmed_duration_sec: float | None = None
    silence_trimmed: bool = False


class AudioExtractor:
    """
    Canonical FFmpeg CLI audio extractor producing 16 kHz mono 16-bit PCM WAV.

    Features:
    1. FFmpeg CLI subprocess invocation with list arguments and shell=False.
    2. Resampling to 16,000 Hz, 1 channel (mono), 16-bit PCM (pcm_s16le).
    3. EBU R128 loudness normalization with JSON measurement extraction.
    4. Configurable silence trimming (default disabled to preserve A-V PTS synchronization).
    5. Source-duration synchronization check against FFprobe container duration using
       the authoritative Row 03 tolerance of +/-2.0 seconds.
    """

    DEFAULT_TIMEOUT_SEC: ClassVar[float] = 120.0
    ROW03_DURATION_TOLERANCE_SEC: ClassVar[float] = 2.0
    DEFAULT_LOUDNORM_TARGET_I: ClassVar[float] = -23.0
    DEFAULT_LOUDNORM_LRA: ClassVar[float] = 7.0
    DEFAULT_LOUDNORM_TP: ClassVar[float] = -2.0
    DEFAULT_SILENCE_THRESHOLD_DB: ClassVar[float] = -50.0
    DEFAULT_SILENCE_DURATION_SEC: ClassVar[float] = 0.2

    def __init__(
        self,
        sample_rate: int | None = None,
        channels: int | None = None,
        sample_width_bytes: int | None = None,
        enable_loudnorm: bool | None = None,
        loudnorm_target_i: float | None = None,
        loudnorm_lra: float | None = None,
        loudnorm_tp: float | None = None,
        enable_silence_trimming: bool | None = None,
        silence_threshold_db: float | None = None,
        silence_duration_sec: float | None = None,
        duration_tolerance_sec: float | None = None,
        timeout_sec: float | None = None,
        gatekeeper: ValidationGatekeeper | None = None,
    ):
        self.sample_rate = (
            sample_rate if sample_rate is not None else settings.audio_sample_rate
        )
        self.channels = channels if channels is not None else settings.audio_channels
        self.sample_width_bytes = (
            sample_width_bytes
            if sample_width_bytes is not None
            else settings.audio_sample_width_bytes
        )
        self.enable_loudnorm = (
            enable_loudnorm
            if enable_loudnorm is not None
            else settings.audio_enable_loudnorm
        )
        self.loudnorm_target_i = (
            loudnorm_target_i
            if loudnorm_target_i is not None
            else settings.audio_loudnorm_target_i
        )
        self.loudnorm_lra = (
            loudnorm_lra
            if loudnorm_lra is not None
            else settings.audio_loudnorm_lra
        )
        self.loudnorm_tp = (
            loudnorm_tp
            if loudnorm_tp is not None
            else settings.audio_loudnorm_tp
        )
        self.enable_silence_trimming = (
            enable_silence_trimming
            if enable_silence_trimming is not None
            else settings.audio_enable_silence_trimming
        )
        self.silence_threshold_db = (
            silence_threshold_db
            if silence_threshold_db is not None
            else settings.audio_silence_threshold_db
        )
        self.silence_duration_sec = (
            silence_duration_sec
            if silence_duration_sec is not None
            else settings.audio_silence_duration_sec
        )
        self.duration_tolerance_sec = (
            duration_tolerance_sec
            if duration_tolerance_sec is not None
            else settings.audio_duration_tolerance_sec
        )
        self.timeout_sec = timeout_sec or self.DEFAULT_TIMEOUT_SEC
        self._gatekeeper = gatekeeper or ValidationGatekeeper()

    @staticmethod
    def calculate_duration_sync(
        source_video_duration_sec: float,
        audio_duration_sec: float,
        tolerance_sec: float = ROW03_DURATION_TOLERANCE_SEC,
    ) -> DurationSyncResult:
        """
        Calculates duration synchronization delta and tolerance compliance.

        delta = audio_duration - source_video_duration
        PASS when abs(delta) <= tolerance_sec (+/-2.0s).
        """
        delta = round(audio_duration_sec - source_video_duration_sec, 4)
        is_ok = abs(delta) <= tolerance_sec
        return DurationSyncResult(
            source_video_duration_sec=round(source_video_duration_sec, 4),
            audio_duration_sec=round(audio_duration_sec, 4),
            duration_difference_sec=delta,
            tolerance_sec=tolerance_sec,
            is_within_tolerance=is_ok,
        )

    @staticmethod
    def parse_loudnorm_json(stderr_text: str) -> LoudnessMeasurement | None:
        """
        Extracts and parses EBU R128 loudnorm JSON diagnostics from FFmpeg stderr output.

        Returns None honestly if JSON block is missing or unparseable.
        """
        pattern = r"(\{\s*\"input_i\"\s*:\s*\"[^\"]+\"[\s\S]*?\})"
        match = re.search(pattern, stderr_text)
        if not match:
            return None
        try:
            data = json.loads(match.group(1))
            return LoudnessMeasurement.from_dict(data)
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.warning("Failed to parse loudnorm JSON from FFmpeg stderr: %s", e)
            return None

    def _execute_ffmpeg(
        self,
        cmd: list[str],
        context_name: str,
    ) -> subprocess.CompletedProcess[str]:
        """
        Executes an FFmpeg CLI command with robust timeout and error handling.
        """
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_sec,
                check=False,
            )
            return res
        except subprocess.TimeoutExpired as e:
            raise AudioExtractionTimeoutError(
                f"FFmpeg command timed out after {self.timeout_sec}s for {context_name}"
            ) from e
        except FileNotFoundError as e:
            raise AudioExtractionError("FFmpeg binary not found on system PATH.") from e
        except Exception as e:
            raise AudioExtractionError(
                f"FFmpeg execution failed for {context_name}: {e}"
            ) from e

    def extract_to_file(
        self,
        video_path: str | Path,
        output_path: str | Path | None = None,
        enable_loudnorm: bool | None = None,
        enable_silence_trimming: bool | None = None,
        strict_duration_sync: bool = False,
    ) -> ExtractedAudio:
        """
        Extracts, resamples, and processes the audio stream from a video to a 16 kHz mono PCM WAV file.

        Args:
            video_path: Path to the input video file.
            output_path: Destination WAV path. If None, generates a temporary file.
            enable_loudnorm: Override for EBU R128 loudness normalization.
            enable_silence_trimming: Override for silence trimming.
            strict_duration_sync: If True, raises DurationSyncMismatchError if duration delta > +/-2.0s.

        Returns:
            ExtractedAudio dataclass containing extracted file metadata and validation metrics.

        Raises:
            InvalidInputError: If file is missing, empty, or a directory.
            NoAudioStreamError: If file has no audio stream.
            CorruptAudioStreamError: If audio bitstream is corrupt or unreadable.
            AudioExtractionTimeoutError: If FFmpeg execution times out.
            AudioExtractionError: If FFmpeg fails or output fails audio specification.
            DurationSyncMismatchError: If strict_duration_sync=True and duration sync fails.
        """
        path = Path(video_path).resolve()

        # Step 1: Pre-validation via ValidationGatekeeper (enforcing Day 1-Day 3 rules)
        v_res = self._gatekeeper.validate(path, strict=False)
        if not v_res.is_valid:
            # Re-run with strict=True to raise typed exception (InvalidInputError, CorruptMediaError, etc.)
            self._gatekeeper.validate(path, strict=True)

        # Step 2: Probe media streams and verify presence of audio stream
        try:
            meta = extract_metadata_ffprobe(path)
        except VideoProcessingError:
            raise
        except Exception as e:
            raise CorruptMediaError(f"Failed to probe media streams for {path.name}") from e

        if not meta.audio_codec:
            raise NoAudioStreamError(f"No audio stream found in media file: {path.name}")

        use_loudnorm = (
            enable_loudnorm if enable_loudnorm is not None else self.enable_loudnorm
        )
        use_silence_trimming = (
            enable_silence_trimming
            if enable_silence_trimming is not None
            else self.enable_silence_trimming
        )

        # Step 3: Determine target output path
        temp_file_created = False
        if output_path is None:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                target_out = Path(tmp.name)
            temp_file_created = True
        else:
            target_out = Path(output_path).resolve()
            target_out.parent.mkdir(parents=True, exist_ok=True)

        # Step 4: Build FFmpeg audio extraction command
        # When silence trimming is requested, we extract to a temporary file first so that
        # we can accurately measure the raw/resampled audio duration for A-V duration synchronization
        # before applying the destructive silence trimming filter.
        if use_silence_trimming:
            with tempfile.NamedTemporaryFile(suffix="_raw.wav", delete=False) as tmp_raw:
                raw_work_file = Path(tmp_raw.name)
        else:
            raw_work_file = target_out


        audio_filters: list[str] = []
        if use_loudnorm:
            audio_filters.append(
                f"loudnorm=I={self.loudnorm_target_i}:LRA={self.loudnorm_lra}:tp={self.loudnorm_tp}:print_format=json"
            )

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(path),
            "-vn",
        ]
        if audio_filters:
            cmd.extend(["-af", ",".join(audio_filters)])
        cmd.extend([
            "-acodec",
            "pcm_s16le",
            "-ar",
            str(self.sample_rate),
            "-ac",
            str(self.channels),
            str(raw_work_file),
        ])

        t0 = time.perf_counter()
        res = self._execute_ffmpeg(cmd, path.name)
        extraction_time = time.perf_counter() - t0

        if res.returncode != 0:
            if temp_file_created and target_out.exists():
                target_out.unlink()
            if raw_work_file.exists() and raw_work_file != target_out:
                raw_work_file.unlink()
            stderr_lower = res.stderr.lower()
            if "invalid data found" in stderr_lower or "corrupt" in stderr_lower:
                raise CorruptAudioStreamError(
                    f"Corrupt or unreadable audio stream in {path.name}"
                )
            raise AudioExtractionError(
                f"FFmpeg extraction returned non-zero exit code {res.returncode} for {path.name}"
            )

        # Parse EBU R128 loudness measurement diagnostics
        loudness_measurement = (
            self.parse_loudnorm_json(res.stderr) if use_loudnorm else None
        )

        # Step 5: Inspect and validate extracted raw WAV properties
        if not raw_work_file.exists() or raw_work_file.stat().st_size == 0:
            if temp_file_created and target_out.exists():
                target_out.unlink()
            if raw_work_file.exists() and raw_work_file != target_out:
                raw_work_file.unlink()
            raise AudioExtractionError(
                f"Extraction produced empty or missing WAV file for {path.name}"
            )

        try:
            with wave.open(str(raw_work_file), "rb") as wf:
                channels = wf.getnchannels()
                sr = wf.getframerate()
                sw = wf.getsampwidth()
                nf = wf.getnframes()
                raw_duration = round(nf / float(sr), 3) if sr > 0 else 0.0
        except wave.Error as e:
            if temp_file_created and target_out.exists():
                target_out.unlink()
            if raw_work_file.exists() and raw_work_file != target_out:
                raw_work_file.unlink()
            raise CorruptAudioStreamError(
                f"Extracted WAV file is corrupt: {e}"
            ) from e

        if (
            channels != self.channels
            or sr != self.sample_rate
            or sw != self.sample_width_bytes
        ):
            if temp_file_created and target_out.exists():
                target_out.unlink()
            if raw_work_file.exists() and raw_work_file != target_out:
                raw_work_file.unlink()
            raise AudioExtractionError(
                f"Extracted WAV properties mismatch: expected {self.sample_rate}Hz, "
                f"{self.channels}ch, {self.sample_width_bytes}B, got {sr}Hz, {channels}ch, {sw}B"
            )

        # Step 6: Duration synchronization check using authoritative Row 03 tolerance (+/-2.0s)
        # Compare source video FFprobe duration against the raw/resampled audio duration
        duration_sync = self.calculate_duration_sync(
            source_video_duration_sec=meta.duration_sec,
            audio_duration_sec=raw_duration,
            tolerance_sec=self.duration_tolerance_sec,
        )

        if strict_duration_sync and not duration_sync.is_within_tolerance:
            if temp_file_created and target_out.exists():
                target_out.unlink()
            if raw_work_file.exists() and raw_work_file != target_out:
                raw_work_file.unlink()
            raise DurationSyncMismatchError(
                f"Duration synchronization failed for {path.name}: "
                f"audio duration {raw_duration}s deviates from source video duration "
                f"{meta.duration_sec}s by {duration_sync.duration_difference_sec}s "
                f"(tolerance: +/-{self.duration_tolerance_sec}s)"
            )

        # Step 7: Silence trimming if enabled
        trimmed_duration: float | None = None
        silence_trimmed = False

        if use_silence_trimming:
            trim_filter = (
                f"silenceremove=start_periods=1:start_duration={self.silence_duration_sec}:"
                f"start_threshold={self.silence_threshold_db}dB:"
                f"stop_periods=1:stop_duration={self.silence_duration_sec}:"
                f"stop_threshold={self.silence_threshold_db}dB"
            )
            cmd_trim = [
                "ffmpeg",
                "-y",
                "-i",
                str(raw_work_file),
                "-af",
                trim_filter,
                "-acodec",
                "pcm_s16le",
                "-ar",
                str(self.sample_rate),
                "-ac",
                str(self.channels),
                str(target_out),
            ]
            res_trim = self._execute_ffmpeg(cmd_trim, f"{path.name} (silence trimming)")
            if raw_work_file.exists():
                raw_work_file.unlink()

            if res_trim.returncode != 0:
                if temp_file_created and target_out.exists():
                    target_out.unlink()
                raise AudioExtractionError(
                    f"Silence trimming failed for {path.name}: {res_trim.stderr[-300:]}"
                )

            with wave.open(str(target_out), "rb") as wf:
                channels = wf.getnchannels()
                sr = wf.getframerate()
                sw = wf.getsampwidth()
                nf = wf.getnframes()
                trimmed_duration = round(nf / float(sr), 3) if sr > 0 else 0.0

            silence_trimmed = True

        final_duration = trimmed_duration if silence_trimmed and trimmed_duration is not None else raw_duration
        final_size = target_out.stat().st_size

        return ExtractedAudio(
            file_path=target_out,
            duration_sec=final_duration,
            raw_duration_sec=raw_duration,
            sample_rate=sr,
            channels=channels,
            sample_width_bytes=sw,
            file_size_bytes=final_size,
            num_frames=nf,
            extraction_time_sec=round(extraction_time, 4),
            loudness_measurement=loudness_measurement,
            duration_sync=duration_sync,
            trimmed_duration_sec=trimmed_duration,
            silence_trimmed=silence_trimmed,
        )

    def extract_to_memory(self, video_path: str | Path) -> bytes:
        """
        Extracts audio and returns the raw PCM WAV bytes.
        Cleans up the temporary file automatically.
        """
        audio = self.extract_to_file(video_path)
        try:
            with open(audio.file_path, "rb") as f:
                return f.read()
        finally:
            if audio.file_path.exists():
                audio.file_path.unlink()
