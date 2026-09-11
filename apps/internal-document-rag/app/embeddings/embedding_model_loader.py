"""
app/embeddings/embedding_model_loader.py — Embedding model loader helper.

Provides `load_embedding_model` function for loading and retrieving
the cached SentenceTransformer embedding model singleton.
"""

from __future__ import annotations

from typing import Any
from app.embeddings.embedding_engine import EmbeddingEngine


def load_embedding_model(model_name: str) -> Any:
    """Load and return the cached singleton embedding model."""
    return EmbeddingEngine._load_model(model_name)
