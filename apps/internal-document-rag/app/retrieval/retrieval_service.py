"""
app/retrieval/retrieval_service.py — Backwards-compatibility shim.

All classes and symbols have moved to app.retrieval.retrieval_engine.
This module re-exports everything so that existing imports continue to work
without modification during and after the rename migration.
"""

from __future__ import annotations

from app.retrieval.retrieval_engine import (  # noqa: F401
    ChromaQueryError,
    EmptyQuestionError,
    InsufficientInformationError,
    QuestionEmbeddingError,
    RetrievalEngine,
    RetrievalEngine as RetrievalService,
    RetrievalEngineError,
    RetrievalServiceError,
    detect_language,
)

__all__ = [
    "ChromaQueryError",
    "EmptyQuestionError",
    "InsufficientInformationError",
    "QuestionEmbeddingError",
    "RetrievalEngine",
    "RetrievalEngineError",
    "RetrievalService",
    "RetrievalServiceError",
]
