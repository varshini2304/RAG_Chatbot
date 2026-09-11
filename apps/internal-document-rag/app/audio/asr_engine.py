"""
app/audio/asr_engine.py — Faster-Whisper Automatic Speech Recognition (ASR) Engine

Provides CPU-optimized speech transcription, language auto-detection, word-level
timestamps, and Real-Time Factor (RTF) telemetry using Faster-Whisper.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.audio.exceptions import ASRModelLoadError, ASRTranscriptionError
from app.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WordTimestamp:
    """Encapsulates a single transcribed word with precise timing and confidence."""

    word: str
    start: float
    end: float
    probability: float | None = None
    confidence: float | None = None

    def __post_init__(self) -> None:
        if self.confidence is None and self.probability is not None:
            object.__setattr__(self, "confidence", self.probability)
        elif self.probability is None and self.confidence is not None:
            object.__setattr__(self, "probability", self.confidence)

    def to_dict(self) -> dict[str, Any]:
        """Serializes word into a JSON-compatible dictionary."""
        d: dict[str, Any] = {
            "word": self.word,
            "start": round(self.start, 4),
            "end": round(self.end, 4),
        }
        conf = self.confidence if self.confidence is not None else self.probability
        if conf is not None:
            d["confidence"] = round(conf, 4)
        return d


@dataclass(frozen=True)
class TranscriptionSegment:
    """Encapsulates a transcribed speech segment."""

    id: int
    start: float
    end: float
    text: str
    words: list[WordTimestamp] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serializes segment into a JSON-compatible dictionary."""
        return {
            "id": self.id,
            "start": round(self.start, 4),
            "end": round(self.end, 4),
            "text": self.text,
            "words": [w.to_dict() for w in self.words],
        }


@dataclass(frozen=True)
class TranscriptionResult:
    """Encapsulates the complete transcription output and performance metrics."""

    detected_language: str
    language_probability: float
    audio_duration_sec: float
    transcription_time_sec: float
    rtf: float
    throughput_x: float
    segments: list[TranscriptionSegment]
    full_text: str
    words: list[WordTimestamp]
    model_load_time_sec: float | None = None
    warmup_time_sec: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serializes result into a JSON-compatible dictionary (backwards-compatible)."""
        return {
            "detected_language": self.detected_language,
            "language_probability": round(self.language_probability, 4),
            "audio_duration_sec": round(self.audio_duration_sec, 3),
            "transcription_time_sec": round(self.transcription_time_sec, 4),
            "rtf": round(self.rtf, 4),
            "throughput_x": round(self.throughput_x, 2) if self.throughput_x else None,
            "segment_count": len(self.segments),
            "word_count": len(self.words),
            "full_text": self.full_text,
            "model_load_time_sec": self.model_load_time_sec,
            "warmup_time_sec": self.warmup_time_sec,
            "segments": [
                {
                    "id": s.id,
                    "start": round(s.start, 3),
                    "end": round(s.end, 3),
                    "text": s.text,
                    "word_count": len(s.words),
                }
                for s in self.segments
            ],
            "words": [
                {
                    "word": w.word,
                    "start": round(w.start, 3),
                    "end": round(w.end, 3),
                    "confidence": round(w.confidence, 4) if w.confidence is not None else None,
                    "prob": round(w.probability, 3) if w.probability is not None else None,
                }
                for w in self.words
            ],
        }

    def to_step_ready_dict(self) -> dict[str, Any]:
        """
        Produces the structured Step-ready dictionary contract for downstream consumption (Step 4).
        """
        return {
            "detected_language": self.detected_language,
            "language_probability": round(self.language_probability, 4),
            "audio_duration_sec": round(self.audio_duration_sec, 3),
            "full_text": self.full_text,
            "segment_count": len(self.segments),
            "word_count": len(self.words),
            "segments": [s.to_dict() for s in self.segments],
            "words": [w.to_dict() for w in self.words],
        }

    def to_step_ready_json(self, indent: int = 2) -> str:
        """Serializes Step-ready dictionary to valid UTF-8 JSON string."""
        import json

        return json.dumps(self.to_step_ready_dict(), indent=indent, ensure_ascii=False)

    def validate_word_timestamps(self) -> list[str]:
        """
        Validates basic consistency and integrity of emitted word-level timestamps:
        - Word text is non-empty string.
        - Start and end timestamps are numeric floats.
        - Start <= end (non-negative duration).
        - Start timestamp >= 0.0.
        - If confidence is present, 0.0 <= confidence <= 1.0.
        - Words appear in chronological sequence within each segment.

        Returns:
            List of error description strings. Empty list indicates full validation PASS.
        """
        errors: list[str] = []
        for i, w in enumerate(self.words):
            if not isinstance(w.word, str) or len(w.word.strip()) == 0:
                errors.append(f"Word at index {i} has empty or non-string text")
            if not isinstance(w.start, (int, float)) or not isinstance(w.end, (int, float)):
                errors.append(f"Word '{w.word}' at index {i} has non-numeric timestamps: start={w.start}, end={w.end}")
            else:
                if w.start < 0.0:
                    errors.append(f"Word '{w.word}' at index {i} has negative start timestamp: {w.start}")
                if w.end < w.start:
                    errors.append(f"Word '{w.word}' at index {i} has end < start: {w.end} < {w.start}")
            conf = w.confidence if w.confidence is not None else w.probability
            if conf is not None and (not isinstance(conf, (int, float)) or conf < 0.0 or conf > 1.0):
                errors.append(f"Word '{w.word}' at index {i} has invalid confidence value: {conf}")

        # Check chronological consistency within segments
        for seg in self.segments:
            for j in range(len(seg.words) - 1):
                curr_w = seg.words[j]
                next_w = seg.words[j + 1]
                if curr_w.start > next_w.start:
                    errors.append(
                        f"Segment {seg.id} words out of chronological order: "
                        f"'{curr_w.word}' ({curr_w.start}s) > '{next_w.word}' ({next_w.start}s)"
                    )

        return errors


class ASREngine:
    """
    Faster-Whisper speech-to-text inference engine optimized for CPU with int8 quantization.
    """

    def __init__(
        self,
        model_size: str | None = None,
        compute_type: str | None = None,
        device: str | None = None,
        beam_size: int | None = None,
        vad_filter: bool | None = None,
        word_timestamps: bool | None = None,
    ):
        self.model_size = model_size or settings.whisper_model_size
        self.compute_type = compute_type or settings.whisper_compute_type
        self.device = device or settings.whisper_device
        self.beam_size = beam_size or settings.whisper_beam_size
        self.vad_filter = (
            vad_filter if vad_filter is not None else settings.whisper_vad_filter
        )
        self.word_timestamps = (
            word_timestamps
            if word_timestamps is not None
            else settings.whisper_word_timestamps
        )
        self._model: Any = None
        self.model_load_time_sec: float | None = None
        self.warmup_time_sec: float | None = None

    @property
    def is_model_loaded(self) -> bool:
        """Returns True if the underlying WhisperModel is loaded in memory."""
        return self._model is not None

    def load_model(self, force: bool = False) -> float:
        """
        Explicitly loads the Faster-Whisper model into memory.
        Reuses the existing model instance if already loaded unless force=True.

        Returns:
            model_load_time_sec: Elapsed time in seconds to load the model.

        Raises:
            ASRModelLoadError: If model initialization or weight loading fails.
        """
        if self._model is not None and not force:
            return self.model_load_time_sec or 0.0

        logger.info(
            "Loading Faster-Whisper model '%s' (compute=%s, device=%s)",
            self.model_size,
            self.compute_type,
            self.device,
        )
        t0 = time.perf_counter()
        try:
            from faster_whisper import WhisperModel  # type: ignore[import-untyped]

            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            self.model_load_time_sec = round(time.perf_counter() - t0, 4)
            logger.info("Faster-Whisper model loaded in %.4fs", self.model_load_time_sec)
            return self.model_load_time_sec
        except Exception as e:
            self._model = None
            logger.error("Failed to load Faster-Whisper model '%s': %s", self.model_size, e)
            raise ASRModelLoadError(
                f"Failed to load faster-whisper model '{self.model_size}' on {self.device}: {e}"
            ) from e

    def warmup(self) -> float:
        """
        Performs a warm-up inference run on a synthetic audio buffer
        to initialize CTranslate2 thread pools, memory allocations, and execution kernels.

        Returns:
            warmup_time_sec: Elapsed time in seconds for the warm-up call.

        Raises:
            ASRModelLoadError: If model cannot be loaded.
            ASRTranscriptionError: If warm-up inference fails.
        """
        model = self._get_model()
        t0 = time.perf_counter()
        try:
            import numpy as np

            # 1-second synthetic 16kHz silence buffer (float32 PCM)
            silence_buffer = np.zeros(16000, dtype=np.float32)
            segments, _ = model.transcribe(silence_buffer, vad_filter=False, beam_size=1)
            _ = list(segments)
            self.warmup_time_sec = round(time.perf_counter() - t0, 4)
            logger.info("Faster-Whisper warm-up completed in %.4fs", self.warmup_time_sec)
            return self.warmup_time_sec
        except Exception as e:
            logger.error("Faster-Whisper warm-up failed: %s", e)
            raise ASRTranscriptionError(f"ASR warm-up failed: {e}") from e

    def _get_model(self):
        """Lazily loads the WhisperModel if not already explicitly loaded."""
        if self._model is None:
            self.load_model()
        return self._model

    def transcribe(
        self,
        audio_path: str | Path,
        language: str | None = None,
        beam_size: int | None = None,
        vad_filter: bool | None = None,
        word_timestamps: bool | None = None,
    ) -> TranscriptionResult:
        """
        Transcribes the input audio file.

        Args:
            audio_path: Path to the 16 kHz mono WAV file.
            language: Optional language code ('en', 'ja'). If None, auto-detects.
            beam_size: Optional beam search size override.
            vad_filter: Optional VAD filter override.
            word_timestamps: Optional word timestamps override.

        Returns:
            TranscriptionResult dataclass with segments, word timestamps, and RTF metrics.

        Raises:
            ASRTranscriptionError: If audio file is missing, corrupt, or transcription fails.
        """
        path = Path(audio_path).resolve()
        if not path.exists():
            raise ASRTranscriptionError(f"Audio file not found: {path.name}")
        if not path.is_file():
            raise ASRTranscriptionError(f"Audio path is not a regular file: {path.name}")
        if path.stat().st_size == 0:
            raise ASRTranscriptionError(f"Audio file is empty: {path.name}")

        model = self._get_model()
        b_size = beam_size or self.beam_size
        v_filter = vad_filter if vad_filter is not None else self.vad_filter
        w_ts = word_timestamps if word_timestamps is not None else self.word_timestamps

        t0 = time.perf_counter()
        try:
            segments_gen, info = model.transcribe(
                str(path),
                language=language,
                beam_size=b_size,
                vad_filter=v_filter,
                word_timestamps=w_ts,
            )

            segments: list[TranscriptionSegment] = []
            all_words: list[WordTimestamp] = []
            full_text_parts: list[str] = []

            for i, seg in enumerate(segments_gen):
                words_in_seg: list[WordTimestamp] = []
                if w_ts and getattr(seg, "words", None):
                    for w in seg.words:
                        raw_prob = getattr(w, "probability", None)
                        prob_val = round(float(raw_prob), 4) if raw_prob is not None else None
                        wt = WordTimestamp(
                            word=w.word.strip(),
                            start=round(float(w.start), 4),
                            end=round(float(w.end), 4),
                            probability=prob_val,
                            confidence=prob_val,
                        )
                        words_in_seg.append(wt)
                        all_words.append(wt)

                s_obj = TranscriptionSegment(
                    id=i,
                    start=round(float(seg.start), 4),
                    end=round(float(seg.end), 4),
                    text=seg.text.strip(),
                    words=words_in_seg,
                )
                segments.append(s_obj)
                full_text_parts.append(seg.text.strip())

        except Exception as e:
            raise ASRTranscriptionError(
                f"Transcription failed for {path.name}: {e}"
            ) from e

        elapsed = time.perf_counter() - t0
        audio_dur = float(getattr(info, "duration", 0.0))
        rtf = (elapsed / audio_dur) if audio_dur > 0 else 0.0
        throughput = (1.0 / rtf) if rtf > 0 else 0.0

        return TranscriptionResult(
            detected_language=getattr(info, "language", language or "unknown"),
            language_probability=float(getattr(info, "language_probability", 1.0)),
            audio_duration_sec=round(audio_dur, 3),
            transcription_time_sec=round(elapsed, 4),
            rtf=round(rtf, 4),
            throughput_x=round(throughput, 2),
            segments=segments,
            full_text=" ".join(full_text_parts),
            words=all_words,
            model_load_time_sec=self.model_load_time_sec,
            warmup_time_sec=self.warmup_time_sec,
        )


# ---------------------------------------------------------------------------
# Backwards-compatibility alias — existing code that imports ASRService
# continues to work without modification during the migration period.
# ---------------------------------------------------------------------------
ASRService = ASREngine
