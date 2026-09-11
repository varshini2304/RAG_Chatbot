"""
app/vision/vision_service.py — Backwards-compatibility shim.

All classes and symbols have moved to app.vision.vision_engine.
This module re-exports everything so that existing imports continue to work
without modification during and after the rename migration.
"""

from __future__ import annotations

from app.vision.vision_engine import (  # noqa: F401
    VisionEngine,
    VisionEngine as VisionService,
)

__all__ = [
    "VisionEngine",
    "VisionService",
]
