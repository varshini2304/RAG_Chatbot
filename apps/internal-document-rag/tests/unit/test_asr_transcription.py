"""
tests/unit/test_asr_transcription.py — Unit Tests for Speech Recognition (ASR) & Alignment

Tests:
1. ASRService initialization with CPU int8 quantization.
2. Transcription segment and word-level timestamp generation.
3. Error handling on missing, empty, or corrupt audio.
4. TimestampAlignmentEvaluator tolerance and error calculation.
5. WERCEREvaluator metric calculation and PENDING status when ground truth is missing.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.audio.alignment import (
    AlignmentAnnotation,
    TimestampAlignmentEvaluator,
    WERCEREvaluator,
)
from app.audio.asr_service import (
    ASRService,
    TranscriptionResult,
    TranscriptionSegment,
    WordTimestamp,
)
from app.audio.exceptions import ASRModelLoadError, ASRTranscriptionError

PROJECT_ROOT = Path(__file__).resolve().parents[3].parent
VIDEOS_DIR = PROJECT_ROOT / "RND" / "02_docs_and_video" / "videos"


class TestASRService:
    """Tests ASR transcription logic and lifecycle using Faster-Whisper."""

    def test_default_configuration(self):
        """Verifies default ASR configuration parameters match authoritative settings."""
        service = ASRService()
        assert service.model_size == "base"
        assert service.compute_type == "int8"
        assert service.device == "cpu"
        assert service.beam_size == 5
        assert service.vad_filter is True
        assert service.word_timestamps is True
        assert not service.is_model_loaded

    def test_custom_configuration(self):
        """Verifies custom configuration overrides are preserved."""
        service = ASRService(
            model_size="tiny",
            compute_type="float32",
            device="cpu",
            beam_size=3,
            vad_filter=False,
            word_timestamps=False,
        )
        assert service.model_size == "tiny"
        assert service.compute_type == "float32"
        assert service.beam_size == 3
        assert service.vad_filter is False
        assert service.word_timestamps is False

    def test_model_loading_and_reuse(self):
        """Verifies explicit model loading initializes the model and reuses the instance."""
        service = ASRService()
        mock_model = MagicMock()
        with patch("faster_whisper.WhisperModel", return_value=mock_model) as mock_cls:
            load_time_1 = service.load_model()
            assert service.is_model_loaded is True
            assert mock_cls.call_count == 1
            assert load_time_1 >= 0.0

            # Second call should reuse existing model instance
            load_time_2 = service.load_model()
            assert service.is_model_loaded is True
            assert mock_cls.call_count == 1
            assert load_time_2 == load_time_1

            # Force reload should re-instantiate
            service.load_model(force=True)
            assert mock_cls.call_count == 2

    def test_model_loading_failure_raises_typed_error(self):
        """Verifies model loading failure raises typed ASRModelLoadError."""
        service = ASRService()
        with patch(
            "faster_whisper.WhisperModel",
            side_effect=RuntimeError("Model weights corrupt"),
        ):
            with pytest.raises(ASRModelLoadError) as exc_info:
                service.load_model()
            assert "Failed to load faster-whisper model" in str(exc_info.value)
            assert not service.is_model_loaded

    def test_warmup_execution(self):
        """Verifies warm-up runs inference on synthetic audio and records telemetry."""
        service = ASRService()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([], MagicMock())
        service._model = mock_model

        warmup_time = service.warmup()
        assert warmup_time >= 0.0
        assert service.warmup_time_sec == warmup_time
        assert mock_model.transcribe.call_count == 1

    def test_warmup_failure_raises_typed_error(self):
        """Verifies warm-up failure raises typed ASRTranscriptionError."""
        service = ASRService()
        mock_model = MagicMock()
        mock_model.transcribe.side_effect = RuntimeError("Inference kernel fault")
        service._model = mock_model

        with pytest.raises(ASRTranscriptionError) as exc_info:
            service.warmup()
        assert "ASR warm-up failed" in str(exc_info.value)

    def test_missing_audio_raises_asr_transcription_error(self):
        """Verifies missing audio file raises ASRTranscriptionError."""
        service = ASRService()
        with pytest.raises(ASRTranscriptionError) as exc_info:
            service.transcribe("non_existent_audio_sample_9999.wav")
        assert "Audio file not found" in str(exc_info.value)

    def test_directory_input_raises_asr_transcription_error(self, tmp_path: Path):
        """Verifies directory path input raises ASRTranscriptionError."""
        service = ASRService()
        with pytest.raises(ASRTranscriptionError) as exc_info:
            service.transcribe(tmp_path)
        assert "Audio path is not a regular file" in str(exc_info.value)

    def test_empty_audio_raises_asr_transcription_error(self, tmp_path: Path):
        """Verifies empty (0 byte) file input raises ASRTranscriptionError."""
        service = ASRService()
        empty_wav = tmp_path / "empty.wav"
        empty_wav.write_bytes(b"")
        with pytest.raises(ASRTranscriptionError) as exc_info:
            service.transcribe(empty_wav)
        assert "Audio file is empty" in str(exc_info.value)

    def test_transcription_result_serialization(self):
        """Validates that TranscriptionResult serializes into dictionary cleanly."""
        res = TranscriptionResult(
            detected_language="en",
            language_probability=0.99,
            audio_duration_sec=10.5,
            transcription_time_sec=1.2,
            rtf=0.1143,
            throughput_x=8.75,
            segments=[
                TranscriptionSegment(
                    id=0,
                    start=0.0,
                    end=2.5,
                    text="Hello machine",
                    words=[
                        WordTimestamp(word="Hello", start=0.0, end=0.8, probability=0.98),
                        WordTimestamp(word="machine", start=0.9, end=2.5, probability=0.95),
                    ],
                )
            ],
            full_text="Hello machine",
            words=[
                WordTimestamp(word="Hello", start=0.0, end=0.8, probability=0.98),
                WordTimestamp(word="machine", start=0.9, end=2.5, probability=0.95),
            ],
            model_load_time_sec=1.0426,
            warmup_time_sec=0.1523,
        )

        d = res.to_dict()
        assert d["detected_language"] == "en"
        assert d["segment_count"] == 1
        assert d["word_count"] == 2
        assert d["segments"][0]["text"] == "Hello machine"
        assert d["words"][0]["word"] == "Hello"
        assert d["model_load_time_sec"] == 1.0426
        assert d["warmup_time_sec"] == 0.1523

    def test_english_word_level_timestamps_structure(self):
        """Verifies WordTimestamp dataclass structure, validity constraints, and serialization."""
        wt = WordTimestamp(word="safety", start=1.60, end=2.05, probability=0.985)
        assert wt.word == "safety"
        assert wt.start == 1.60
        assert wt.end == 2.05
        assert wt.start <= wt.end
        assert 0.0 <= wt.probability <= 1.0

        seg = TranscriptionSegment(
            id=0,
            start=1.60,
            end=2.05,
            text="safety",
            words=[wt],
        )
        assert len(seg.words) == 1
        assert seg.words[0].word == "safety"

    def test_japanese_word_level_timestamps_structure(self):
        """Verifies Japanese characters in WordTimestamp dataclass and TranscriptionSegment."""
        wt1 = WordTimestamp(word="こんにちは", start=11.85, end=12.20, probability=0.985)
        assert wt1.word == "こんにちは"
        assert wt1.start == 11.85
        assert wt1.end == 12.20
        assert wt1.start <= wt1.end
        assert 0.0 <= wt1.probability <= 1.0
        assert wt1.confidence == 0.985

        wt2 = WordTimestamp(word="それでは", start=13.65, end=14.15, probability=0.970)
        seg = TranscriptionSegment(
            id=0,
            start=11.85,
            end=14.15,
            text="こんにちは。それでは",
            words=[wt1, wt2],
        )
        assert len(seg.words) == 2
        assert seg.words[0].word == "こんにちは"
        assert seg.words[1].word == "それでは"

    def test_word_timestamp_confidence_preservation(self):
        """Verifies actual probability is preserved as confidence without 1.0 fabrication."""
        # Case 1: Probability provided -> confidence matches probability exactly
        wt1 = WordTimestamp(word="safety", start=1.60, end=2.05, probability=0.9852)
        assert wt1.confidence == 0.9852
        assert wt1.probability == 0.9852
        d1 = wt1.to_dict()
        assert d1["word"] == "safety"
        assert d1["confidence"] == 0.9852

        # Case 2: Explicit confidence provided -> probability mirrors confidence
        wt2 = WordTimestamp(word="mill", start=1.30, end=1.55, confidence=0.9412)
        assert wt2.confidence == 0.9412
        assert wt2.probability == 0.9412
        assert wt2.to_dict()["confidence"] == 0.9412

        # Case 3: No probability or confidence provided -> remains None without fabrication
        wt3 = WordTimestamp(word="basic", start=0.95, end=1.25)
        assert wt3.confidence is None
        assert wt3.probability is None
        d3 = wt3.to_dict()
        assert "confidence" not in d3

    def test_transcription_result_step_ready_dict_and_json(self):
        """Validates Step-ready output schema and JSON serialization."""
        import json

        wt = WordTimestamp(word="safety", start=1.60, end=2.05, probability=0.985)
        seg = TranscriptionSegment(id=0, start=1.60, end=2.05, text="safety", words=[wt])
        res = TranscriptionResult(
            detected_language="en",
            language_probability=0.99,
            audio_duration_sec=5.0,
            transcription_time_sec=0.5,
            rtf=0.1,
            throughput_x=10.0,
            segments=[seg],
            full_text="safety",
            words=[wt],
        )

        step_dict = res.to_step_ready_dict()
        assert step_dict["detected_language"] == "en"
        assert step_dict["word_count"] == 1
        assert len(step_dict["words"]) == 1
        assert step_dict["words"][0]["word"] == "safety"
        assert step_dict["words"][0]["start"] == 1.6
        assert step_dict["words"][0]["end"] == 2.05
        assert step_dict["words"][0]["confidence"] == 0.985

        # Check JSON serialization
        json_str = res.to_step_ready_json()
        parsed = json.loads(json_str)
        assert parsed["words"][0]["confidence"] == 0.985
        assert parsed["segment_count"] == 1

    def test_validate_word_timestamps_passes_on_valid_data(self):
        """Verifies validate_word_timestamps returns empty list for valid data."""
        w1 = WordTimestamp(word="basic", start=0.95, end=1.25, confidence=0.95)
        w2 = WordTimestamp(word="mill", start=1.30, end=1.55, confidence=0.90)
        seg = TranscriptionSegment(id=0, start=0.95, end=1.55, text="basic mill", words=[w1, w2])
        res = TranscriptionResult(
            detected_language="en",
            language_probability=1.0,
            audio_duration_sec=2.0,
            transcription_time_sec=0.2,
            rtf=0.1,
            throughput_x=10.0,
            segments=[seg],
            full_text="basic mill",
            words=[w1, w2],
        )
        assert res.validate_word_timestamps() == []

    def test_validate_word_timestamps_catches_invalid_data(self):
        """Verifies validate_word_timestamps catches non-monotonic timestamps, end < start, and empty text."""
        w1 = WordTimestamp(word="", start=-0.5, end=0.5, confidence=1.5)  # empty text, negative start, invalid conf
        w2 = WordTimestamp(word="invalid", start=1.5, end=1.0)  # end < start
        seg = TranscriptionSegment(id=0, start=0.0, end=2.0, text="err", words=[w2, w1])  # out of order: 1.5 > -0.5
        res = TranscriptionResult(
            detected_language="en",
            language_probability=1.0,
            audio_duration_sec=2.0,
            transcription_time_sec=0.2,
            rtf=0.1,
            throughput_x=10.0,
            segments=[seg],
            full_text="err",
            words=[w1, w2],
        )
        errors = res.validate_word_timestamps()
        assert len(errors) >= 4
        assert any("empty or non-string" in e for e in errors)
        assert any("negative start" in e for e in errors)
        assert any("end < start" in e for e in errors)
        assert any("invalid confidence" in e for e in errors)


class TestTimestampAlignmentEvaluator:
    """Tests word timestamp evaluation against ground-truth annotations."""

    @pytest.fixture
    def evaluator(self) -> TimestampAlignmentEvaluator:
        return TimestampAlignmentEvaluator(tolerance_sec=0.5)

    def test_evaluate_within_tolerance(self, evaluator: TimestampAlignmentEvaluator):
        mock_result = TranscriptionResult(
            detected_language="en",
            language_probability=0.99,
            audio_duration_sec=5.0,
            transcription_time_sec=0.5,
            rtf=0.1,
            throughput_x=10.0,
            segments=[
                TranscriptionSegment(
                    id=0,
                    start=0.0,
                    end=3.0,
                    text="Today we talk mill safety",
                    words=[
                        WordTimestamp(word="Today", start=0.05, end=0.30),
                        WordTimestamp(word="talk", start=0.70, end=0.88),
                    ],
                )
            ],
            full_text="Today we talk mill safety",
            words=[
                WordTimestamp(word="Today", start=0.05, end=0.30),
                WordTimestamp(word="talk", start=0.70, end=0.88),
            ],
        )

        annotations = [
            AlignmentAnnotation(phrase="Today", expected_start=0.00, expected_end=0.35),
            AlignmentAnnotation(phrase="talk", expected_start=0.65, expected_end=0.90),
        ]

        report = evaluator.evaluate(mock_result, annotations, language="en")
        assert report.total_annotations == 2
        assert report.within_tolerance_count == 2
        assert report.accuracy_pct == 100.0
        assert report.mean_start_error_sec is not None
        assert report.mean_start_error_sec <= 0.5

    def test_evaluate_phrase_not_found(self, evaluator: TimestampAlignmentEvaluator):
        mock_result = TranscriptionResult(
            detected_language="en",
            language_probability=0.99,
            audio_duration_sec=5.0,
            transcription_time_sec=0.5,
            rtf=0.1,
            throughput_x=10.0,
            segments=[],
            full_text="Nothing here",
            words=[],
        )

        annotations = [
            AlignmentAnnotation(phrase="missingword", expected_start=1.0, expected_end=2.0)
        ]

        report = evaluator.evaluate(mock_result, annotations, language="en")
        assert report.total_annotations == 1
        assert report.within_tolerance_count == 0
        assert report.accuracy_pct == 0.0
        assert report.phrase_results[0].status == "NOT_FOUND"

    def test_evaluator_calculation_logic(self, evaluator: TimestampAlignmentEvaluator):
        """
        Pure calculation unit test: verifies that evaluator correctly calculates
        within-tolerance count, start/end errors, mean errors, and accuracy percentage
        without hardcoded empirical expectations.
        """
        mock_result = TranscriptionResult(
            detected_language="en",
            language_probability=0.99,
            audio_duration_sec=10.0,
            transcription_time_sec=1.0,
            rtf=0.1,
            throughput_x=10.0,
            segments=[
                TranscriptionSegment(
                    id=0,
                    start=0.0,
                    end=5.0,
                    text="word1 word2 word3",
                    words=[
                        WordTimestamp(word="word1", start=1.0, end=2.0),
                        WordTimestamp(word="word2", start=3.0, end=4.0),
                        WordTimestamp(word="word3", start=5.0, end=6.0),
                    ],
                )
            ],
            full_text="word1 word2 word3",
            words=[
                WordTimestamp(word="word1", start=1.0, end=2.0),
                WordTimestamp(word="word2", start=3.0, end=4.0),
                WordTimestamp(word="word3", start=5.0, end=6.0),
            ],
        )

        test_annotations = [
            # Case 1: Exact match (err = 0.0, within 0.5s tolerance) -> PASS
            AlignmentAnnotation(phrase="word1", expected_start=1.0, expected_end=2.0),
            # Case 2: Within tolerance (start_err = 0.2, end_err = 0.2, within 0.5s) -> PASS
            AlignmentAnnotation(phrase="word2", expected_start=2.8, expected_end=3.8),
            # Case 3: Exceeds tolerance (start_err = 1.0, end_err = 1.0, > 0.5s) -> EXCEEDS_TOLERANCE
            AlignmentAnnotation(phrase="word3", expected_start=4.0, expected_end=5.0),
            # Case 4: Missing phrase -> NOT_FOUND
            AlignmentAnnotation(phrase="word_absent", expected_start=7.0, expected_end=8.0),
        ]

        report = evaluator.evaluate(mock_result, test_annotations, language="en")
        assert report.total_annotations == 4
        assert report.matched_count == 3
        assert report.within_tolerance_count == 2
        # Accuracy: 2 / 4 * 100 = 50.0%
        assert report.accuracy_pct == 50.0
        assert report.phrase_results[0].status == "PASS"
        assert report.phrase_results[1].status == "PASS"
        assert report.phrase_results[2].status == "EXCEEDS_TOLERANCE"
        assert report.phrase_results[3].status == "NOT_FOUND"

        # Check mean errors on matched items:
        # word1: start_err=0.0, end_err=0.0
        # word2: start_err=0.2, end_err=0.2
        # word3: start_err=1.0, end_err=1.0
        # mean_start_err = (0.0 + 0.2 + 1.0) / 3 = 0.4
        # mean_end_err = (0.0 + 0.2 + 1.0) / 3 = 0.4
        assert report.mean_start_error_sec == pytest.approx(0.4, abs=0.001)
        assert report.mean_end_error_sec == pytest.approx(0.4, abs=0.001)

    def test_japanese_timestamp_alignment_evaluation(self, evaluator: TimestampAlignmentEvaluator):
        """Verifies TimestampAlignmentEvaluator with Japanese annotations and phrases."""
        mock_result = TranscriptionResult(
            detected_language="ja",
            language_probability=0.985,
            audio_duration_sec=15.0,
            transcription_time_sec=1.5,
            rtf=0.1,
            throughput_x=10.0,
            segments=[
                TranscriptionSegment(
                    id=0,
                    start=11.80,
                    end=12.25,
                    text="こんにちは。",
                    words=[WordTimestamp(word="こんにちは", start=11.82, end=12.20, probability=0.99)],
                ),
                TranscriptionSegment(
                    id=1,
                    start=13.60,
                    end=14.20,
                    text="それでは作業を始めます。",
                    words=[
                        WordTimestamp(word="それでは", start=13.64, end=14.12, probability=0.98),
                        WordTimestamp(word="作業", start=14.15, end=14.40, probability=0.95),
                    ],
                ),
            ],
            full_text="こんにちは。それでは作業を始めます。",
            words=[
                WordTimestamp(word="こんにちは", start=11.82, end=12.20, probability=0.99),
                WordTimestamp(word="それでは", start=13.64, end=14.12, probability=0.98),
                WordTimestamp(word="作業", start=14.15, end=14.40, probability=0.95),
            ],
        )

        annotations = [
            AlignmentAnnotation(phrase="こんにちは", expected_start=11.85, expected_end=12.20),
            AlignmentAnnotation(phrase="それでは", expected_start=13.65, expected_end=14.15),
        ]

        report = evaluator.evaluate(mock_result, annotations, language="ja")
        assert report.total_annotations == 2
        assert report.matched_count == 2
        assert report.within_tolerance_count == 2
        assert report.accuracy_pct == 100.0
        assert report.mean_start_error_sec is not None
        assert report.mean_start_error_sec <= 0.5
        assert report.mean_end_error_sec is not None
        assert report.mean_end_error_sec <= 0.5



class TestWERCEREvaluator:
    """Tests Word Error Rate and Character Error Rate calculation."""

    def test_exact_match_yields_zero_error(self):
        ref = "Turn on the milling machine spindle."
        hyp = "Turn on the milling machine spindle."
        wer = WERCEREvaluator.calculate_wer(ref, hyp)
        cer = WERCEREvaluator.calculate_cer(ref, hyp)
        assert wer == 0.0
        assert cer == 0.0

    def test_word_substitution_calculation(self):
        ref = "Turn on the milling machine."
        hyp = "Turn off the milling machine."  # 1 substitution out of 5 words
        wer = WERCEREvaluator.calculate_wer(ref, hyp)
        assert wer == 0.2

    def test_missing_reference_reports_pending_status(self):
        res = WERCEREvaluator.evaluate(None, "Hypothesis text from whisper.")
        assert res["status"] == "PENDING / STAKEHOLDER INPUT REQUIRED"
        assert res["reference_provided"] is False
        assert res["wer"] is None
        assert res["cer"] is None

    def test_japanese_cer_calculation(self):
        """Verifies CER calculation on Japanese character sequences."""
        ref = "こんにちはそれでは"
        hyp = "こんばんはそれでは"
        cer = WERCEREvaluator.calculate_cer(ref, hyp)
        assert cer > 0.0
        assert cer <= 1.0

        ref_exact = "それでは、これから作業を始めます。"
        cer_exact = WERCEREvaluator.calculate_cer(ref_exact, ref_exact)
        assert cer_exact == 0.0
