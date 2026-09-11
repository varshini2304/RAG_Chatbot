"""
tests/integration/test_asr_integration.py — Integration Tests for Step 3 ASR (faster-whisper base int8 CPU)

Verifies:
1. Model configuration and explicit loading mechanism.
2. Model warm-up step execution and timing telemetry.
3. Model instance reuse across multiple transcription invocations.
4. Real transcription call on standardized Day 4 WAV (16 kHz mono PCM).
5. Non-empty transcription output and structured segment generation.
6. Language auto-detection on real English and Japanese repository fixtures.
7. RTF and throughput calculation using actual measured execution times.
8. Safe error handling on missing / invalid inputs.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pytest

from app.audio.alignment import TimestampAlignmentEvaluator
from app.audio.asr_service import ASRService, TranscriptionResult
from app.audio.exceptions import ASRTranscriptionError
from app.config import settings

PROJECT_ROOT = Path(__file__).resolve().parents[3].parent
VIDEOS_DIR = PROJECT_ROOT / "RND" / "02_docs_and_video" / "videos"


def extract_clip_wav(
    video_path: Path,
    out_wav: Path,
    duration_sec: float = 15.0,
) -> None:
    """
    Extracts a short standardized 16 kHz mono 16-bit PCM WAV clip
    from a video fixture using FFmpeg CLI, matching Day 4 specifications.
    """
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-t",
        str(duration_sec),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        str(settings.audio_sample_rate),
        "-ac",
        str(settings.audio_channels),
        str(out_wav),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg audio extraction failed: {res.stderr}")


@pytest.fixture(scope="module")
def asr_service() -> ASRService:
    """Provides a shared ASRService instance with explicit lifecycle management."""
    service = ASRService(
        model_size=settings.whisper_model_size,
        compute_type=settings.whisper_compute_type,
        device=settings.whisper_device,
    )
    # Explicit model load
    load_time = service.load_model()
    assert service.is_model_loaded is True
    assert load_time > 0.0

    # Explicit warm-up
    warmup_time = service.warmup()
    assert warmup_time > 0.0

    return service


class TestASRIntegration:
    """Integration test suite for Faster-Whisper ASR pipeline on CPU."""

    def test_english_instructional_transcription(self, asr_service: ASRService):
        """
        Tests transcription of real English instructional fixture (test_instructional_normal.mp4).
        Verifies non-empty transcript, detected language, and records actual RTF.
        """
        video_path = VIDEOS_DIR / "test_instructional_normal.mp4"
        assert video_path.exists(), f"Missing fixture: {video_path}"

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = Path(tmp.name)

        try:
            # 1. Extract standardized 15-second WAV clip
            extract_clip_wav(video_path, wav_path, duration_sec=15.0)
            assert wav_path.stat().st_size > 0

            # 2. Transcribe
            res = asr_service.transcribe(wav_path)

            # 3. Assertions without invented thresholds
            assert isinstance(res, TranscriptionResult)
            assert len(res.full_text.strip()) > 0, "Transcription text must be non-empty"
            assert res.detected_language == "en", f"Expected 'en', got '{res.detected_language}'"
            assert res.language_probability > 0.0, "Language probability must be recorded"
            assert len(res.segments) > 0, "Segment count must be greater than 0"
            assert res.audio_duration_sec > 0.0
            assert res.transcription_time_sec > 0.0
            assert res.rtf > 0.0

            # Verify segment structure
            for seg in res.segments:
                assert seg.start >= 0.0
                assert seg.end >= seg.start
                assert len(seg.text) > 0

            # Verify word-level timestamps structure
            assert len(res.words) > 0, "Word timestamps must be populated when enabled"
            for wt in res.words:
                assert wt.start >= 0.0, f"Word '{wt.word}' has negative start timestamp"
                assert wt.end >= wt.start, f"Word '{wt.word}' has end < start"
                assert len(wt.word) > 0, "Word text must be non-empty"
                assert 0.0 <= wt.probability <= 1.0, f"Word '{wt.word}' probability out of [0, 1]"

            # Verify telemetry is populated
            assert res.model_load_time_sec is not None
            assert res.warmup_time_sec is not None

            # Log actual measured performance
            print(
                f"\n[EN Benchmark] Duration={res.audio_duration_sec:.2f}s | "
                f"Inference={res.transcription_time_sec:.4f}s | "
                f"RTF={res.rtf:.4f} ({res.throughput_x:.2f}x) | "
                f"Lang={res.detected_language} (p={res.language_probability:.4f}) | "
                f"Segments={len(res.segments)}"
            )
        finally:
            if wav_path.exists():
                wav_path.unlink()

    def test_clean_japanese_transcription(self, asr_service: ASRService):
        """
        Tests transcription of real Japanese clean fixture (const_01.mp4).
        Verifies non-empty transcript, detected language (ja), segment timestamps,
        word-level timestamps, and records actual RTF telemetry.
        """
        video_path = VIDEOS_DIR / "const_01.mp4"
        assert video_path.exists(), f"Missing fixture: {video_path}"

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = Path(tmp.name)

        try:
            # 1. Extract standardized 15-second WAV clip
            extract_clip_wav(video_path, wav_path, duration_sec=15.0)
            assert wav_path.stat().st_size > 0

            # 2. Transcribe
            res = asr_service.transcribe(wav_path, word_timestamps=True)

            # 3. Assertions without invented thresholds
            assert isinstance(res, TranscriptionResult)
            assert len(res.full_text.strip()) > 0, "Transcription text must be non-empty"
            assert res.detected_language == "ja", f"Expected 'ja', got '{res.detected_language}'"
            assert res.language_probability > 0.0, "Language probability must be recorded"
            assert len(res.segments) > 0, "Segment count must be greater than 0"
            assert res.rtf > 0.0

            # Verify segment structure
            for seg in res.segments:
                assert seg.start >= 0.0
                assert seg.end >= seg.start
                assert len(seg.text) > 0

            # Verify Japanese word/token timestamps structure
            assert len(res.words) > 0, "Japanese word timestamps must be populated when enabled"
            for wt in res.words:
                assert wt.start >= 0.0, f"Token '{wt.word}' has negative start timestamp"
                assert wt.end >= wt.start, f"Token '{wt.word}' has end < start"
                assert len(wt.word) > 0, "Token text must be non-empty"
                assert 0.0 <= wt.probability <= 1.0, f"Token '{wt.word}' probability out of [0, 1]"

            print(
                f"\n[JA Clean Benchmark] Duration={res.audio_duration_sec:.2f}s | "
                f"Inference={res.transcription_time_sec:.4f}s | "
                f"RTF={res.rtf:.4f} ({res.throughput_x:.2f}x) | "
                f"Lang={res.detected_language} (p={res.language_probability:.4f}) | "
                f"Segments={len(res.segments)} | Words={len(res.words)}"
            )
        finally:
            if wav_path.exists():
                wav_path.unlink()

    def test_noisy_japanese_transcription(self, asr_service: ASRService):
        """
        Tests transcription of real noisy Japanese fixture (Working_on_machine_noisy.mp4).
        Verifies ASR stability under noise, Japanese auto-detection, segment structure,
        and word-level timestamp generation.
        """
        video_path = VIDEOS_DIR / "Working_on_machine_noisy.mp4"
        assert video_path.exists(), f"Missing fixture: {video_path}"

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = Path(tmp.name)

        try:
            # 1. Extract standardized 15-second WAV clip
            extract_clip_wav(video_path, wav_path, duration_sec=15.0)
            assert wav_path.stat().st_size > 0

            # 2. Transcribe
            res = asr_service.transcribe(wav_path, word_timestamps=True)

            # 3. Assertions without invented thresholds
            assert isinstance(res, TranscriptionResult)
            assert len(res.full_text.strip()) > 0, "Transcription text must be non-empty"
            assert res.detected_language == "ja", f"Expected 'ja', got '{res.detected_language}'"
            assert res.language_probability > 0.0, "Language probability must be recorded"
            assert len(res.segments) > 0, "Segment count must be greater than 0"
            assert res.rtf > 0.0

            # Verify segment structure
            for seg in res.segments:
                assert seg.start >= 0.0
                assert seg.end >= seg.start
                assert len(seg.text) > 0

            # Verify word-level timestamps under noise
            assert len(res.words) > 0, "Word timestamps must be populated under noise"
            for wt in res.words:
                assert wt.start >= 0.0, f"Token '{wt.word}' has negative start"
                assert wt.end >= wt.start, f"Token '{wt.word}' has end < start"
                assert len(wt.word) > 0, "Token text must be non-empty"
                assert 0.0 <= wt.probability <= 1.0

            print(
                f"\n[JA Noisy Benchmark] Duration={res.audio_duration_sec:.2f}s | "
                f"Inference={res.transcription_time_sec:.4f}s | "
                f"RTF={res.rtf:.4f} ({res.throughput_x:.2f}x) | "
                f"Lang={res.detected_language} (p={res.language_probability:.4f}) | "
                f"Segments={len(res.segments)} | Words={len(res.words)}"
            )
        finally:
            if wav_path.exists():
                wav_path.unlink()

    def test_row06_japanese_word_level_sync_benchmark(self, asr_service: ASRService):
        """
        Executes Row 06 Japanese word-level synchronization benchmark against authoritative
        ground truth (n=2, tolerance ±0.5s).
        Verifies evaluator execution, structural integrity of the report, and calculations,
        without hardcoding expected accuracy outcomes into the test assertion.
        """
        video_path = VIDEOS_DIR / "const_01.mp4"
        assert video_path.exists(), f"Missing fixture: {video_path}"

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = Path(tmp.name)

        try:
            extract_clip_wav(video_path, wav_path, duration_sec=15.0)
            res = asr_service.transcribe(wav_path, language="ja", word_timestamps=True)

            evaluator = TimestampAlignmentEvaluator(tolerance_sec=0.5)
            annotations = evaluator.GROUND_TRUTH_ANNOTATIONS["const_01.mp4"]
            report = evaluator.evaluate(res, annotations, language="ja")

            # 1. Structural evaluation assertions
            assert report.total_annotations == 2, "Both Japanese annotations must be evaluated"
            assert report.matched_count == 2, "Both Japanese annotations must be matched in transcript"
            assert len(report.phrase_results) == 2

            # 2. Calculation correctness assertions
            expected_pct = round((report.within_tolerance_count / report.total_annotations) * 100.0, 2)
            assert report.accuracy_pct == expected_pct

            # 3. Per-phrase structural verification
            for pr in report.phrase_results:
                assert pr.actual_start is not None
                assert pr.actual_end is not None
                assert pr.start_error_sec is not None
                assert pr.end_error_sec is not None
                assert pr.within_tolerance == (
                    pr.start_error_sec <= report.tolerance_sec
                    and pr.end_error_sec <= report.tolerance_sec
                )
                assert pr.status in ("PASS", "EXCEEDS_TOLERANCE")

            # 4. Mean error metric integrity
            assert report.mean_start_error_sec is not None
            assert report.mean_start_error_sec >= 0.0
            assert report.mean_end_error_sec is not None
            assert report.mean_end_error_sec >= 0.0

            # Telemetry logging for empirical inspection (no artificial assertion on outcome)
            baseline_accuracy = 100.0
            difference = round(report.accuracy_pct - baseline_accuracy, 2)

            print(
                f"\n[Row 06 JA Benchmark Execution] "
                f"Evaluated={report.total_annotations} | "
                f"Within Tolerance={report.within_tolerance_count}/{report.total_annotations} | "
                f"Accuracy={report.accuracy_pct:.2f}% | "
                f"Baseline={baseline_accuracy:.1f}% (from n=2) | "
                f"Difference={difference:+.2f}% | "
                f"Mean Start Err={report.mean_start_error_sec:.4f}s | "
                f"Mean End Err={report.mean_end_error_sec:.4f}s"
            )
        finally:
            if wav_path.exists():
                wav_path.unlink()

    def test_model_reuse_across_calls(self, asr_service: ASRService):
        """
        Verifies that the underlying model instance is preserved across multiple calls
        without re-initialization or memory re-allocation.
        """
        initial_model = asr_service._model
        assert initial_model is not None

        # Call load_model again
        load_time = asr_service.load_model()
        assert asr_service._model is initial_model, "Model instance must be reused"
        assert load_time == asr_service.model_load_time_sec

    def test_missing_wav_input_error_handling(self, asr_service: ASRService):
        """Verifies safe error handling on non-existent audio input."""
        with pytest.raises(ASRTranscriptionError) as exc_info:
            asr_service.transcribe("non_existent_fixture_audio_0000.wav")
        assert "Audio file not found" in str(exc_info.value)

    def test_row06_word_level_sync_benchmark_execution(self, asr_service: ASRService):
        """
        Executes Row 06 word-level synchronization benchmark against authoritative ground truth.
        Verifies evaluator execution, structural integrity of the report, and calculations,
        without hardcoding expected accuracy outcomes into the test assertion.
        """
        video_path = VIDEOS_DIR / "test_instructional_normal.mp4"
        assert video_path.exists(), f"Missing fixture: {video_path}"

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = Path(tmp.name)

        try:
            extract_clip_wav(video_path, wav_path, duration_sec=15.0)
            res = asr_service.transcribe(wav_path, language="en", word_timestamps=True)

            evaluator = TimestampAlignmentEvaluator(tolerance_sec=0.5)
            annotations = evaluator.GROUND_TRUTH_ANNOTATIONS["test_instructional_normal.mp4"]
            report = evaluator.evaluate(res, annotations, language="en")

            # 1. Structural evaluation assertions
            assert report.total_annotations == 7, "All 7 annotations must be evaluated"
            assert report.matched_count == 7, "All 7 annotations must be matched in transcript"
            assert len(report.phrase_results) == 7

            # 2. Calculation correctness assertions
            expected_pct = round((report.within_tolerance_count / report.total_annotations) * 100.0, 2)
            assert report.accuracy_pct == expected_pct

            # 3. Per-phrase structural verification
            for pr in report.phrase_results:
                assert pr.actual_start is not None
                assert pr.actual_end is not None
                assert pr.start_error_sec is not None
                assert pr.end_error_sec is not None
                assert pr.within_tolerance == (
                    pr.start_error_sec <= report.tolerance_sec
                    and pr.end_error_sec <= report.tolerance_sec
                )
                assert pr.status in ("PASS", "EXCEEDS_TOLERANCE")

            # 4. Mean error metric integrity
            assert report.mean_start_error_sec is not None
            assert report.mean_start_error_sec >= 0.0
            assert report.mean_end_error_sec is not None
            assert report.mean_end_error_sec >= 0.0

            # Telemetry logging for empirical inspection (no artificial assertion on outcome)
            baseline_accuracy = 57.1
            improvement = round(report.accuracy_pct - baseline_accuracy, 2)
            buffer_threshold = 70.0
            threshold_reached = report.accuracy_pct >= buffer_threshold

            print(
                f"\n[Row 06 Benchmark Execution] "
                f"Evaluated={report.total_annotations} | "
                f"Within Tolerance={report.within_tolerance_count}/{report.total_annotations} | "
                f"Accuracy={report.accuracy_pct:.2f}% | "
                f"Baseline={baseline_accuracy:.1f}% | "
                f"Improvement={improvement:+.2f}% | "
                f"Threshold 70%: {'MET' if threshold_reached else 'NOT REACHED'} | "
                f"Mean Start Err={report.mean_start_error_sec:.4f}s | "
                f"Mean End Err={report.mean_end_error_sec:.4f}s"
            )
        finally:
            if wav_path.exists():
                wav_path.unlink()

