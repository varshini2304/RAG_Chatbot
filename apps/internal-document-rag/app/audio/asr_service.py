"""
app/audio/asr_service.py — Backwards-compatibility shim.

All classes and symbols have moved to app.audio.asr_engine.
This module re-exports everything so that existing imports continue to work
without modification during and after the rename migration.
"""

from app.audio.asr_engine import (  # noqa: F401
    ASREngine,
    ASREngine as ASRService,
    TranscriptionResult,
    TranscriptionSegment,
    WordTimestamp,
)

__all__ = [
    "ASREngine",
    "ASRService",
    "TranscriptionResult",
    "TranscriptionSegment",
    "WordTimestamp",
]
