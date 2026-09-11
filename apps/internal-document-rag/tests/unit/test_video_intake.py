"""
test_video_intake.py — Unit Tests for Step 2 Video Intake Module
Tests in-memory PyAV demuxing, stream detection, MP4/WebM/VFR support, and error handling.
"""

import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pytest

from app.video.exceptions import (
    CorruptMediaError,
    InvalidInputError,
    NoVideoStreamError,
    UnsupportedContainerError,
    VideoProcessingError,
)
from app.video.video_loader import VideoLoader, probe_container_ffprobe

# Location of benchmark video fixtures
VIDEOS_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "RND" / "02_docs_and_video" / "videos"

VALID_TEST_VIDEOS = [
    "test_instructional_normal.mp4",
    "const_01.mp4",
    "Working on machine.mp4",
    "Working_on_machine_noisy.mp4",
    "Ubiquitous-Robotic-Technology-for-Smart-Manufacturing-System-6018686.f1.ogv.240p.vp9.webm",
    "controlled_vfr_test.mp4",
    "controlled_synthetic_corrupt.mp4",
]


@pytest.fixture(params=VALID_TEST_VIDEOS)
def video_file(request) -> Path:
    """Fixture providing each of the 7 known video test assets."""
    path = VIDEOS_DIR / request.param
    assert path.exists(), f"Test asset not found: {path}"
    return path


class TestVideoLoaderIngestion:
    """Tests covering all 7 known R&D video assets."""

    def test_container_metadata_extraction(self, video_file: Path):
        """Verify container metadata extraction for valid video files."""
        with VideoLoader(video_file) as loader:
            meta = loader.get_metadata()
            assert meta.format_name != ""
            assert meta.duration_sec > 0.0
            assert len(meta.video_streams) >= 1

            v = meta.primary_video_stream
            assert v is not None
            assert v.width > 0
            assert v.height > 0
            assert v.codec_name != ""
            assert v.duration_sec > 0.0

    def test_first_frame_decode(self, video_file: Path):
        """Verify initial frame decoding into RGB ndarray."""
        with VideoLoader(video_file) as loader:
            frame = loader.decode_first_frame()
            assert frame is not None
            assert isinstance(frame.data, np.ndarray)
            assert frame.data.shape == (frame.height, frame.width, 3)
            assert frame.data.dtype == np.uint8
            assert frame.format == "RGB24"

    def test_ffprobe_cross_validation(self, video_file: Path):
        """Verify external ffprobe CLI wrapper parses container."""
        probe = probe_container_ffprobe(video_file)
        assert "streams" in probe
        assert "format" in probe
        assert len(probe["streams"]) >= 1


class TestContainerFormats:
    """Tests specifically validating MP4, WebM (VP9), and VFR handling."""

    def test_webm_vp9_stream(self):
        """Verify WebM container with VP9 video stream."""
        webm_path = VIDEOS_DIR / "Ubiquitous-Robotic-Technology-for-Smart-Manufacturing-System-6018686.f1.ogv.240p.vp9.webm"
        with VideoLoader(webm_path) as loader:
            meta = loader.get_metadata()
            assert "webm" in meta.format_name.lower() or "matroska" in meta.format_name.lower()
            v_stream = meta.primary_video_stream
            assert v_stream is not None
            assert v_stream.codec_name == "vp9"
            frame = loader.decode_first_frame()
            assert frame.width == 320
            assert frame.height == 240

    def test_vfr_stream(self):
        """Verify Variable Frame Rate (VFR) container."""
        vfr_path = VIDEOS_DIR / "controlled_vfr_test.mp4"
        with VideoLoader(vfr_path) as loader:
            meta = loader.get_metadata()
            assert meta.primary_video_stream is not None
            frame = loader.decode_first_frame()
            assert frame.timestamp_sec >= 0.0

    def test_in_memory_bytes_input(self):
        """Verify in-memory binary bytes input without disk access."""
        sample_path = VIDEOS_DIR / "controlled_vfr_test.mp4"
        with open(sample_path, "rb") as f:
            raw_bytes = f.read()

        with VideoLoader(raw_bytes) as loader:
            meta = loader.get_metadata()
            assert len(meta.video_streams) == 1
            frame = loader.decode_first_frame()
            assert frame.data.shape[2] == 3


class TestErrorHandlingAndValidation:
    """Verify typed exceptions on missing, empty, and corrupt inputs."""

    def test_non_existent_file_raises_invalid_input(self):
        """Non-existent file must raise InvalidInputError."""
        with pytest.raises(InvalidInputError) as exc_info:
            loader = VideoLoader(VIDEOS_DIR / "non_existent_video_file_xyz123.mp4")
            loader.open()
        assert "does not exist" in str(exc_info.value)

    def test_empty_file_raises_invalid_input(self):
        """Zero-byte file must raise InvalidInputError."""
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            with pytest.raises(InvalidInputError) as exc_info:
                loader = VideoLoader(tmp_path)
                loader.open()
            assert "empty (0 bytes)" in str(exc_info.value)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_truncated_header_raises_corrupt_media(self):
        """Truncated MP4 header must raise CorruptMediaError or UnsupportedContainerError."""
        corrupt_bytes = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2mp41\x00\x00\x00\x08free"
        with pytest.raises((CorruptMediaError, UnsupportedContainerError)) as exc_info:
            loader = VideoLoader(corrupt_bytes)
            loader.open()
        assert issubclass(exc_info.type, VideoProcessingError)

    def test_garbage_bytes_raises_corrupt_media(self):
        """Random binary noise must raise typed VideoProcessingError without crash."""
        garbage = os.urandom(2048)
        with pytest.raises(VideoProcessingError) as exc_info:
            loader = VideoLoader(garbage)
            loader.open()
        assert issubclass(exc_info.type, VideoProcessingError)

    def test_directory_target_raises_invalid_input(self):
        """Directory target must raise InvalidInputError."""
        with pytest.raises(InvalidInputError) as exc_info:
            loader = VideoLoader(VIDEOS_DIR)
            loader.open()
        assert "not a regular file" in str(exc_info.value)

    def test_file_size_threshold_exceeded(self):
        """Exceeding configured maximum size must raise InvalidInputError."""
        sample_path = VIDEOS_DIR / "controlled_vfr_test.mp4"
        actual_size = sample_path.stat().st_size
        with pytest.raises(InvalidInputError) as exc_info:
            loader = VideoLoader(sample_path, max_size_bytes=actual_size - 100)
            loader.open()
        assert "exceeds maximum configured limit" in str(exc_info.value)

    def test_audio_only_file_raises_no_video_stream_on_decode(self):
        """Audio-only media container must raise NoVideoStreamError on decode_first_frame."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            # Generate 0.5s silent WAV
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "anullsrc=r=16000:cl=mono",
                    "-t",
                    "0.5",
                    "-acodec",
                    "pcm_s16le",
                    str(tmp_path),
                ],
                capture_output=True,
                check=True,
            )
            with VideoLoader(tmp_path) as loader:
                meta = loader.get_metadata()
                assert len(meta.video_streams) == 0
                assert len(meta.audio_streams) >= 1
                with pytest.raises(NoVideoStreamError) as exc_info:
                    loader.decode_first_frame()
                assert "no video stream" in str(exc_info.value).lower()
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_require_video_stream_flag_raises_on_open(self):
        """When require_video_stream=True, opening an audio-only container raises NoVideoStreamError."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "anullsrc=r=16000:cl=mono",
                    "-t",
                    "0.5",
                    "-acodec",
                    "pcm_s16le",
                    str(tmp_path),
                ],
                capture_output=True,
                check=True,
            )
            with pytest.raises(NoVideoStreamError) as exc_info:
                loader = VideoLoader(tmp_path, require_video_stream=True)
                loader.open()
            assert "contains no video streams" in str(exc_info.value)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
