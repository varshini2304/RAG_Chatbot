"""Embedding engine and pipeline."""

from __future__ import annotations

from app.embeddings.embedding_engine import (
    EmbeddingEngine,
    EmbeddingEngineError,
    EmbeddingService,
    EmbeddingServiceError,
)
from app.embeddings.embedding_model_loader import load_embedding_model
from app.embeddings.embedding_pipeline import (
    EmbeddingPipeline,
    EmbeddingPipelineError,
)

__all__ = [
    "EmbeddingEngine",
    "EmbeddingEngineError",
    "EmbeddingPipeline",
    "EmbeddingPipelineError",
    "EmbeddingService",
    "EmbeddingServiceError",
    "load_embedding_model",
]
