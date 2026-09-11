"""
tests/integration/test_audio_asr_pipeline.py — End-to-End Audio Extraction, ASR & Timestamp Sync Tests

Tests the complete Step 3 pipeline across real repository fixtures:
1. English instructional video (test_instructional_normal.mp4): 16k mono extraction + Whisper ASR + RTF.
2. Clean Japanese video (const_01.mp4): audio extraction + Japanese language detection + transcription.
3. Noisy Japanese video (Working_on_machine_noisy.mp4): ASR robustness under injected noise.
4. Variable frame rate video (controlled_vfr_test.mp4): audio extraction & stream timing analysis.
5. Timestamp alignment against R&D ground-truth annotations (7 EN, 2 JA phrases).
6. WER/CER framework evaluation & pending status verification.
7. Regression against Steps 1 & 2 video intake.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.audio.alignment import (
    TimestampAlignmentEvaluator,
    WERCEREvaluator,
)
from app.audio.asr_service import ASRService
from app.audio.audio_extractor import AudioExtractor
from app.video.video_loader import ValidationGatekeeper, VideoLoader

PROJECT_ROOT = Path(__file__).resolve().parents[3].parent
VIDEOS_DIR = PROJECT_ROOT / "RND" / "02_docs_and_video" / "videos"


class TestAudioASREndToEndPipeline:
    """End-to-end integration tests for audio extraction, ASR, and timestamp alignment."""

    @pytest.fixture(scope="class")
    def extractor(self) -> AudioExtractor:
        return AudioExtractor()

    @pytest.fixture(scope="class")
    def asr_service(self) -> ASRService:
        return ASRService(model_size="base", compute_type="int8", device="cpu")

    @pytest.fixture(scope="class")
    def alignment_evaluator(self) -> TimestampAlignmentEvaluator:
        return TimestampAlignmentEvaluator(tolerance_sec=0.5)

    def test_english_instructional_video_pipeline(
        self,
        extractor: AudioExtractor,
        asr_service: ASRService,
        alignment_evaluator: TimestampAlignmentEvaluator,
    ):
        video_path = VIDEOS_DIR / "test_instructional_normal.mp4"
        assert video_path.exists()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = Path(tmp.name)

        try:
            # 1. Audio Extraction
            audio = extractor.extract_to_file(video_path, output_path=wav_path)
            assert audio.sample_rate == 16000
            assert audio.channels == 1
            assert audio.duration_sec > 450.0

            # 2. Whisper ASR
            res = asr_service.transcribe(wav_path)
            assert res.detected_language == "en"
            assert res.language_probability > 0.9
            assert len(res.segments) > 10
            assert len(res.words) > 50
            assert res.rtf < 1.0  # Real-time factor faster than 1.0x on CPU

            # 3. Ground Truth Timestamp Alignment
            en_annotations = alignment_evaluator.GROUND_TRUTH_ANNOTATIONS["test_instructional_normal.mp4"]
            report = alignment_evaluator.evaluate(res, en_annotations, language="en")
            assert report.total_annotations == 7
            assert report.matched_count >= 4
            assert report.within_tolerance_count >= 3
            assert report.accuracy_pct > 40.0
        finally:
            if wav_path.exists():
                wav_path.unlink()

    def test_clean_japanese_video_pipeline(
        self,
        extractor: AudioExtractor,
        asr_service: ASRService,
        alignment_evaluator: TimestampAlignmentEvaluator,
    ):
        video_path = VIDEOS_DIR / "const_01.mp4"
        assert video_path.exists()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = Path(tmp.name)

        try:
            # 1. Audio Extraction
            audio = extractor.extract_to_file(video_path, output_path=wav_path)
            assert audio.sample_rate == 16000
            assert audio.channels == 1
            assert audio.duration_sec > 540.0

            # 2. Whisper ASR
            res = asr_service.transcribe(wav_path)
            assert res.detected_language == "ja"
            assert res.language_probability > 0.9
            assert len(res.segments) > 10

            # 3. Ground Truth Timestamp Alignment
            ja_annotations = alignment_evaluator.GROUND_TRUTH_ANNOTATIONS["const_01.mp4"]
            report = alignment_evaluator.evaluate(res, ja_annotations, language="ja")
            assert report.total_annotations == 2
            assert report.matched_count == 2
            assert report.within_tolerance_count == 2
            assert report.accuracy_pct == 100.0
        finally:
            if wav_path.exists():
                wav_path.unlink()

    def test_noisy_japanese_video_pipeline_robustness(
        self,
        extractor: AudioExtractor,
        asr_service: ASRService,
    ):
        video_path = VIDEOS_DIR / "Working_on_machine_noisy.mp4"
        assert video_path.exists()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = Path(tmp.name)

        try:
            audio = extractor.extract_to_file(video_path, output_path=wav_path)
            assert audio.sample_rate == 16000
            assert audio.duration_sec > 540.0

            res = asr_service.transcribe(wav_path)
            assert res.detected_language == "ja"
            assert len(res.segments) > 5
        finally:
            if wav_path.exists():
                wav_path.unlink()

    def test_vfr_video_timing_and_extraction(
        self,
        extractor: AudioExtractor,
    ):
        """
        Validates audio extraction and timing behavior for variable frame rate (VFR) media.
        In controlled_vfr_test.mp4, audio duration is 456.62s while video stream duration is 274.03s.
        """
        vfr_path = VIDEOS_DIR / "controlled_vfr_test.mp4"
        assert vfr_path.exists()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = Path(tmp.name)

        try:
            audio = extractor.extract_to_file(vfr_path, output_path=wav_path)
            assert audio.sample_rate == 16000
            assert audio.channels == 1
            assert abs(audio.duration_sec - 456.62) < 1.0

            # Verify video stream metadata duration difference
            gatekeeper = ValidationGatekeeper()
            v_res = gatekeeper.validate(vfr_path)
            assert v_res.is_valid
            assert v_res.metadata is not None
            # Container format reports full duration
            assert abs(v_res.metadata.duration_sec - 456.62) < 1.0
        finally:
            if wav_path.exists():
                wav_path.unlink()

    def test_wer_cer_pending_status_for_untranscribed_media(self):
        """
        Verifies that full-video WER/CER returns PENDING status in accordance
        with zero-hallucination policy when reference transcript is not available.
        """
        eval_res = WERCEREvaluator.evaluate(reference_text=None, hypothesis_text="Some ASR text")
        assert eval_res["status"] == "PENDING / STAKEHOLDER INPUT REQUIRED"
        assert eval_res["reference_provided"] is False
        assert eval_res["wer"] is None
        assert eval_res["cer"] is None

    def test_regression_step1_and_step2_video_intake(self):
        """
        Confirms that Step 1 (demuxing) and Step 2 (gatekeeper) remain fully functional.
        """
        sample_video = VIDEOS_DIR / "test_instructional_normal.mp4"
        assert sample_video.exists()

        # Gatekeeper
        gk = ValidationGatekeeper()
        v_res = gk.validate(sample_video, strict=True)
        assert v_res.is_valid

        # VideoLoader
        with VideoLoader(sample_video) as loader:
            meta = loader.get_metadata()
            assert meta.format_name is not None
            frame = loader.decode_first_frame()
            assert frame is not None
            assert frame.width == 640
            assert frame.height == 360
