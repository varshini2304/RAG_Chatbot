"""
app/ingestion/image_ingestion_service.py — Backwards-compatibility shim.

All classes and symbols have moved to app.ingestion.image_ingestion.
This module re-exports everything so that existing imports continue to work
without modification during and after the rename migration.
"""

from __future__ import annotations

from app.ingestion.image_ingestion import (  # noqa: F401
    ImageIngestion,
    ImageIngestion as ImageIngestionService,
)

__all__ = [
    "ImageIngestion",
    "ImageIngestionService",
]
