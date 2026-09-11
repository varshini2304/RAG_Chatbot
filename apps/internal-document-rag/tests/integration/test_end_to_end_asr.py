"""
tests/integration/test_end_to_end_asr.py — End-to-End ASR Pipeline & Step-Ready Structured Output Test

Validates the full chain:
Raw Video Fixture
  ↓
ValidationGatekeeper (pre-validation)
  ↓
AudioExtractor (16 kHz mono 16-bit PCM WAV extraction)
  ↓
ASRService (faster-whisper base int8 on CPU)
  ↓
Word-level transcription & timestamp validation
  ↓
Step-ready structured JSON output (Step 4 input contract compatibility)
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from app.audio.asr_service import ASRService, TranscriptionResult
from app.audio.audio_extractor import AudioExtractor
from app.config import settings
from app.video.video_loader import ValidationGatekeeper

PROJECT_ROOT = Path(__file__).resolve().parents[3].parent
VIDEOS_DIR = PROJECT_ROOT / "RND" / "02_docs_and_video" / "videos"


class TestEndToEndASRPipeline:
    """Automated pytest test suite verifying the complete Raw Video -> Step-Ready JSON pipeline."""

    @pytest.fixture(scope="class")
    def gatekeeper(self) -> ValidationGatekeeper:
        return ValidationGatekeeper()

    @pytest.fixture(scope="class")
    def extractor(self) -> AudioExtractor:
        return AudioExtractor()

    @pytest.fixture(scope="class")
    def asr_service(self) -> ASRService:
        service = ASRService(
            model_size=settings.whisper_model_size,
            compute_type=settings.whisper_compute_type,
            device=settings.whisper_device,
        )
        service.load_model()
        service.warmup()
        return service

    def test_raw_video_to_step_ready_json_pipeline(
        self,
        gatekeeper: ValidationGatekeeper,
        extractor: AudioExtractor,
        asr_service: ASRService,
    ):
        """
        Executes end-to-end pipeline on raw repository video fixture:
        1. Pre-validates video with ValidationGatekeeper.
        2. Extracts standardized 16 kHz mono PCM WAV using AudioExtractor without API changes.
        3. Transcribes with word-level timestamps using ASRService.
        4. Serializes to Step-ready structured JSON.
        5. Validates word-level timestamps, actual confidence scores, and Step 4 contract compatibility.
        """
        # 1. Raw video fixture verification
        video_path = VIDEOS_DIR / "const_01.mp4"
        assert video_path.exists(), f"Missing fixture: {video_path}"
        assert video_path.is_file()

        # Step 1: ValidationGatekeeper check
        gate_res = gatekeeper.validate(video_path, strict=True)
        assert gate_res.is_valid is True
        assert gate_res.metadata is not None
        assert gate_res.metadata.duration_sec > 0.0

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = Path(tmp.name)

        try:
            # Step 2: Audio extraction via existing AudioExtractor production API
            audio_res = extractor.extract_to_file(video_path, output_path=wav_path)
            assert wav_path.exists()
            assert wav_path.stat().st_size > 0
            assert audio_res.sample_rate == 16000
            assert audio_res.channels == 1
            assert audio_res.duration_sec > 0.0

            # Step 3: ASR Transcription with word timestamps enabled
            res = asr_service.transcribe(wav_path, word_timestamps=True)
            assert isinstance(res, TranscriptionResult)
            assert len(res.full_text.strip()) > 0, "Transcription output must not be empty"
            assert res.detected_language == "ja"
            assert res.language_probability > 0.0
            assert len(res.segments) > 0
            assert len(res.words) > 0

            # Step 4: Step-Ready structured output generation
            step_ready_dict = res.to_step_ready_dict()
            assert isinstance(step_ready_dict, dict)
            assert "detected_language" in step_ready_dict
            assert "audio_duration_sec" in step_ready_dict
            assert "full_text" in step_ready_dict
            assert "segment_count" in step_ready_dict
            assert "word_count" in step_ready_dict
            assert "segments" in step_ready_dict
            assert "words" in step_ready_dict

            # Step 5: Valid JSON serialization check
            json_output = res.to_step_ready_json()
            parsed_json = json.loads(json_output)
            assert isinstance(parsed_json, dict)
            assert parsed_json["word_count"] == len(res.words)
            assert parsed_json["segment_count"] == len(res.segments)

            # Step 6: Validate every word entry in top-level words list
            assert len(step_ready_dict["words"]) > 0
            for idx, w_entry in enumerate(step_ready_dict["words"]):
                assert "word" in w_entry, f"Word entry {idx} missing 'word' field"
                assert "start" in w_entry, f"Word entry {idx} missing 'start' field"
                assert "end" in w_entry, f"Word entry {idx} missing 'end' field"
                assert "confidence" in w_entry, f"Word entry {idx} missing 'confidence' field"

                assert isinstance(w_entry["word"], str)
                assert len(w_entry["word"].strip()) > 0
                assert isinstance(w_entry["start"], (int, float))
                assert isinstance(w_entry["end"], (int, float))
                assert w_entry["start"] >= 0.0
                assert w_entry["end"] >= w_entry["start"]

                # Confidence must be actual probability from model in [0.0, 1.0]
                conf = w_entry["confidence"]
                if conf is not None:
                    assert isinstance(conf, (int, float))
                    assert 0.0 <= conf <= 1.0

            # Step 7: Validate word timestamps consistency via validator
            validation_errors = res.validate_word_timestamps()
            assert validation_errors == [], f"Word timestamp consistency errors: {validation_errors}"

            # Step 8: Step 4 input contract compatibility check
            # Step 4 prototype (row_07_work_step.py) expects segments with 'start', 'end', and 'text'
            for seg in step_ready_dict["segments"]:
                assert "start" in seg
                assert "end" in seg
                assert "text" in seg
                assert "words" in seg
                assert isinstance(seg["words"], list)
                for sw in seg["words"]:
                    assert "word" in sw
                    assert "start" in sw
                    assert "end" in sw
                    assert "confidence" in sw

            print(
                f"\n[E2E Pipeline Success] Video: {video_path.name} | "
                f"Audio Dur: {res.audio_duration_sec:.2f}s | "
                f"Inference: {res.transcription_time_sec:.2f}s | "
                f"RTF: {res.rtf:.4f} | "
                f"Words: {len(res.words)} | Segments: {len(res.segments)} | "
                f"Lang: {res.detected_language} (p={res.language_probability:.4f})"
            )
        finally:
            if wav_path.exists():
                wav_path.unlink()
