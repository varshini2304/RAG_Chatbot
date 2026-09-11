"""
Video Processing Router
=======================
Exposes real video intake, FFprobe container metadata extraction,
and FFmpeg audio extraction endpoints using the existing app/video
and app/audio services.
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse

from app.api.schemas.base import ErrorResponse, ResponseModel
from app.audio.audio_extractor import AudioExtractor
from app.audio.exceptions import NoAudioStreamError
from app.config import settings
from app.video.video_loader import extract_metadata_ffprobe, ValidationGatekeeper

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/video", tags=["Video Processing"])

# Directory containing benchmark fixtures in workspace
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
RND_VIDEOS_DIR = PROJECT_ROOT / "RND" / "02_docs_and_video" / "videos"
APP_UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "uploads" / "videos"
APP_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
WORKSPACE_UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads" / "videos"
WORKSPACE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_VIDEOS_DIR = APP_UPLOAD_DIR


@router.get("/system-info", summary="Get Pipeline & Engine System Information")
def get_system_info():
    """Return runtime pipeline parameters directly from settings and audio/video services."""
    return ResponseModel(
        success=True,
        message="System information retrieved successfully",
        data={
            "asr_model": {
                "name": f"faster-whisper ({settings.whisper_model_size})",
                "model_size": settings.whisper_model_size,
                "compute_type": settings.whisper_compute_type,
                "device": settings.whisper_device,
                "beam_size": settings.whisper_beam_size,
                "vad_filter": settings.whisper_vad_filter,
                "details": f"{settings.whisper_compute_type} • {settings.whisper_device.upper()}",
            },
            "audio_format": {
                "name": "WAV • 16 kHz • Mono",
                "encoding": "PCM 16-bit",
                "sample_rate_hz": 16000,
                "channels": 1,
                "loudness": f"EBU R128 ({settings.audio_loudnorm_target_i} LUFS)",
            },
            "target_languages": {
                "primary": "Japanese (ja)",
                "secondary": "English (en)",
                "supported": ["ja", "en"],
            },
            "processing_mode": {
                "name": "Standard",
                "subtitle": "(High Accuracy)",
                "supported_formats": settings.video_supported_formats,
                "max_size_mb": round(settings.video_max_size_bytes / (1024 * 1024)),
            },
        },
    )


@router.get("/fixtures", summary="List Available Video Fixtures")
def list_video_fixtures():
    """Return available video fixtures from repository RND directory."""
    fixtures = []
    if RND_VIDEOS_DIR.exists():
        for p in RND_VIDEOS_DIR.glob("*.*"):
            if p.suffix.lower().lstrip(".") in settings.video_supported_formats:
                fixtures.append({
                    "filename": p.name,
                    "size_bytes": p.stat().st_size,
                    "path": str(p),
                })
    return ResponseModel(success=True, message="Fixtures listed", data=fixtures)


@router.post("/ingest", summary="Ingest Video & Extract Audio")
async def ingest_video(file: UploadFile = File(...)):
    """
    Accept an uploaded video file, validate container via ValidationGatekeeper,
    extract FFprobe metadata, and standardize audio using AudioExtractor.
    """
    if not file.filename:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                success=False, message="No filename provided.", errors=["Missing filename"]
            ).model_dump(),
        )

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in settings.video_supported_formats:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                success=False,
                message=f"Unsupported video format: .{ext}",
                errors=[f"Supported formats: {settings.video_supported_formats}"],
            ).model_dump(),
        )

    saved_path = UPLOAD_VIDEOS_DIR / file.filename
    with open(saved_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return _process_video_path(saved_path, file.filename)


@router.post("/ingest-fixture/{filename}", summary="Ingest Existing Fixture Video")
def ingest_fixture(filename: str):
    """Run video intake & audio extraction on an existing benchmark fixture."""
    fixture_path = RND_VIDEOS_DIR / filename
    if not fixture_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fixture '{filename}' not found on server.",
        )

    return _process_video_path(fixture_path, filename)


def _process_video_path(video_path: Path, filename: str) -> ResponseModel[dict[str, Any]]:
    """Runs FFprobe metadata extraction and FFmpeg audio extraction."""
    # 1. Video Intake / Metadata
    try:
        gatekeeper = ValidationGatekeeper(max_size_bytes=settings.video_max_size_bytes)
        v_res = gatekeeper.validate(video_path, strict=False)
        meta = v_res.metadata or extract_metadata_ffprobe(video_path)
    except Exception as exc:
        logger.exception("Video metadata extraction failed for %s:", filename)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Video intake failed: {exc}",
        ) from exc

    is_silent = meta.audio_codec is None
    audio_extracted = False
    wav_path = None
    extraction_time = 0.0

    # 2. Audio Extraction (if audio exists)
    if not is_silent:
        try:
            extractor = AudioExtractor()
            res = extractor.extract_to_file(video_path)
            audio_extracted = True
            wav_path = str(res.output_wav_path)
            extraction_time = res.extraction_time_sec
        except NoAudioStreamError:
            is_silent = True
            logger.info("No audio stream detected in %s; ASR will be skipped.", filename)
        except Exception as exc:
            logger.warning("Audio extraction failed for %s: %s", filename, exc)

    return ResponseModel(
        success=True,
        message="Video ingestion and audio extraction completed successfully.",
        data={
            "filename": filename,
            "size_bytes": meta.size_bytes,
            "duration_sec": meta.duration_sec,
            "width": meta.width,
            "height": meta.height,
            "fps": meta.fps,
            "codec": meta.codec,
            "container_format": meta.container_format,
            "audio_codec": meta.audio_codec if not is_silent else None,
            "sample_rate": meta.sample_rate if not is_silent else None,
            "audio_channels": meta.audio_channels if not is_silent else None,
            "is_silent": is_silent,
            "audio_extracted": audio_extracted,
            "wav_path": wav_path,
            "extraction_time_sec": extraction_time,
        },
    )


@router.get("/stream/{filename}", summary="Stream Video File")
def stream_video(filename: str):
    """Stream video file for HTML5 video player with range request support."""
    import urllib.parse
    decoded_name = urllib.parse.unquote(filename)

    for search_dir in [UPLOAD_VIDEOS_DIR, WORKSPACE_UPLOAD_DIR, RND_VIDEOS_DIR, Path("data/uploads/videos")]:
        for candidate_name in [decoded_name, filename]:
            target = search_dir / candidate_name
            if target.exists() and target.is_file():
                suffix = target.suffix.lower()
                media_type = "video/mp4"
                if suffix == ".webm":
                    media_type = "video/webm"
                elif suffix == ".mov":
                    media_type = "video/quicktime"
                elif suffix == ".mkv":
                    media_type = "video/x-matroska"
                elif suffix == ".avi":
                    media_type = "video/x-msvideo"

                return FileResponse(
                    target,
                    media_type=media_type,
                    headers={
                        "Accept-Ranges": "bytes",
                        "Content-Disposition": f'inline; filename="{target.name}"',
                        "Cache-Control": "public, max-age=3600",
                    },
                )

    raise HTTPException(status_code=404, detail=f"Video file '{filename}' not found on server.")
