"""
app/embeddings/embedding_service.py — Backwards-compatibility shim.

All classes and symbols have moved to app.embeddings.embedding_engine.
This module re-exports everything so that existing imports continue to work
without modification during and after the rename migration.
"""

from __future__ import annotations

from app.embeddings.embedding_engine import (  # noqa: F401
    EmbeddingEngine,
    EmbeddingEngine as EmbeddingService,
    EmbeddingEngineError,
    EmbeddingServiceError,
    _normalize_vector,
)

__all__ = [
    "EmbeddingEngine",
    "EmbeddingEngineError",
    "EmbeddingService",
    "EmbeddingServiceError",
]
