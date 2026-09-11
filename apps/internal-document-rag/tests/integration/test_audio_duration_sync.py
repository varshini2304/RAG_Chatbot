"""
tests/integration/test_audio_duration_sync.py — Integration Tests for Audio Duration Synchronization

Validates audio extraction, resampling, EBU R128 normalization, silence trimming,
and source-duration synchronization across real repository video fixtures:
1. test_instructional_normal.mp4 (Normal instructional video)
2. const_01.mp4 (Clean Japanese industrial video)
3. Working_on_machine_noisy.mp4 (Noisy machine operation audio)
4. controlled_vfr_test.mp4 (Variable frame rate video with audio)
5. controlled_synthetic_corrupt.mp4 (Synthetic corrupt/truncated fixture)
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.audio.audio_extractor import (
    AudioExtractor,
    ExtractedAudio,
    LoudnessMeasurement,
)
from app.video.video_loader import extract_metadata_ffprobe

PROJECT_ROOT = Path(__file__).resolve().parents[3].parent
VIDEOS_DIR = PROJECT_ROOT / "RND" / "02_docs_and_video" / "videos"


class TestAudioDurationSyncIntegration:
    """Integration test suite executing audio extraction and duration sync against repository fixtures."""

    @pytest.fixture
    def extractor(self) -> AudioExtractor:
        return AudioExtractor()

    @pytest.mark.parametrize(
        ("video_filename", "expected_audio_codec"),
        [
            ("test_instructional_normal.mp4", "aac"),
            ("const_01.mp4", "aac"),
            ("Working_on_machine_noisy.mp4", "aac"),
            ("controlled_vfr_test.mp4", "aac"),
        ],
    )
    def test_valid_video_duration_sync_within_row03_tolerance(
        self, extractor: AudioExtractor, video_filename: str, expected_audio_codec: str
    ):
        """
        Verifies that for valid media fixtures, extracted audio is 16 kHz mono PCM
        and its duration matches the source video FFprobe duration within the
        authoritative Row 03 tolerance (+/-2.0 seconds).
        """
        video_path = VIDEOS_DIR / video_filename
        assert video_path.exists(), f"Missing required fixture: {video_path}"

        # 1. Inspect source video via FFprobe ground truth
        source_meta = extract_metadata_ffprobe(video_path)
        assert source_meta.audio_codec == expected_audio_codec
        assert source_meta.duration_sec > 0

        # 2. Extract audio and verify properties
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            out_wav = Path(tmp.name)

        try:
            res = extractor.extract_to_file(video_path, output_path=out_wav)
            assert isinstance(res, ExtractedAudio)
            assert res.file_path.exists()
            assert res.sample_rate == 16000
            assert res.channels == 1
            assert res.sample_width_bytes == 2

            # 3. Source duration vs Audio duration check
            assert res.duration_sync is not None
            sync = res.duration_sync
            assert sync.tolerance_sec == 2.0
            assert sync.source_video_duration_sec == round(source_meta.duration_sec, 4)
            assert sync.audio_duration_sec == round(res.raw_duration_sec, 4)

            # delta = audio_duration - source_video_duration
            delta = sync.duration_difference_sec
            assert abs(delta) <= 2.0, (
                f"{video_filename}: Duration delta {delta:.4f}s exceeds +/-2.0s tolerance. "
                f"(Audio: {res.raw_duration_sec}s, Source: {source_meta.duration_sec}s)"
            )
            assert sync.is_within_tolerance is True
        finally:
            if out_wav.exists():
                out_wav.unlink()

    def test_loudnorm_integration_captures_valid_metrics(
        self, extractor: AudioExtractor
    ):
        """Verifies EBU R128 loudness normalization captures valid loudness measurements."""
        video_path = VIDEOS_DIR / "test_instructional_normal.mp4"
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            out_wav = Path(tmp.name)

        try:
            res = extractor.extract_to_file(video_path, output_path=out_wav, enable_loudnorm=True)
            assert res.loudness_measurement is not None
            lm = res.loudness_measurement
            assert isinstance(lm, LoudnessMeasurement)
            assert lm.input_i < 0  # Typical audio LUFS is negative
            assert lm.output_i < 0
            assert -30.0 <= lm.output_i <= -15.0  # Output should be in reasonable normalized range
            assert lm.normalization_type in ("dynamic", "linear")
        finally:
            if out_wav.exists():
                out_wav.unlink()

    def test_silence_trimming_integration_preserves_raw_sync(
        self, extractor: AudioExtractor
    ):
        """
        Verifies that when silence trimming is enabled:
        - raw_duration_sec reflects the un-trimmed audio duration and maintains A-V sync.
        - trimmed_duration_sec reflects the trimmed audio duration.
        - silence_trimmed flag is True.
        """
        video_path = VIDEOS_DIR / "test_instructional_normal.mp4"
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            out_wav = Path(tmp.name)

        try:
            res = extractor.extract_to_file(video_path, output_path=out_wav, enable_silence_trimming=True)
            assert res.silence_trimmed is True
            assert res.trimmed_duration_sec is not None
            assert res.raw_duration_sec > 0
            assert res.duration_sync is not None
            # The A/V sync check must be performed against raw duration, not trimmed duration
            assert res.duration_sync.audio_duration_sec == res.raw_duration_sec
            assert res.duration_sync.is_within_tolerance is True
        finally:
            if out_wav.exists():
                out_wav.unlink()

    def test_controlled_synthetic_corrupt_detected_by_duration_sync(
        self, extractor: AudioExtractor
    ):
        """
        controlled_synthetic_corrupt.mp4 has a valid header indicating ~456s,
        but the audio stream is truncated at ~136s.
        Verifies that duration synchronization correctly marks this as FAIL (delta > +/-2.0s).
        """
        corrupt_path = VIDEOS_DIR / "controlled_synthetic_corrupt.mp4"
        assert corrupt_path.exists()

        source_meta = extract_metadata_ffprobe(corrupt_path)
        assert source_meta.duration_sec > 0
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            out_wav = Path(tmp.name)

        try:
            res = extractor.extract_to_file(corrupt_path, output_path=out_wav)
            assert res.duration_sync is not None
            sync = res.duration_sync
            # Delta should be around -320s
            assert sync.duration_difference_sec < -2.0
            assert sync.is_within_tolerance is False
        finally:
            if out_wav.exists():
                out_wav.unlink()
