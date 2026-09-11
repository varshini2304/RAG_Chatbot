"""Guard check to validate ChromaDB collection dimensions and prevent mismatches."""

from __future__ import annotations

import logging
from typing import Any

LOGGER = logging.getLogger(__name__)


class EmbeddingDimensionMismatchError(ValueError):
    """Raised when the vector database dimension does not match active settings."""


def assert_collection_dimension_matches(
    collection: Any, expected_dimension: int
) -> None:

    metadata = collection.metadata or {}
    stored_dimension = metadata.get("embedding_dimension")

    if stored_dimension is not None:
        try:
            stored_dimension = int(stored_dimension)
        except (ValueError, TypeError):
            stored_dimension = None

    # Fallback to inspecting one stored embedding's vector length if metadata is missing
    if stored_dimension is None:
        try:
            existing = collection.get(limit=1, include=["embeddings"])
            embeddings = existing.get("embeddings")
            if existing and embeddings is not None and len(embeddings) > 0:
                stored_dimension = len(embeddings[0])
                LOGGER.info(
                    "Fallback inspection: detected stored dimension %s for collection %s.",
                    stored_dimension,
                    collection.name,
                )
        except Exception as exc:
            LOGGER.warning(
                "Failed to retrieve existing embedding for dimension fallback: %s", exc
            )

    if stored_dimension is not None and stored_dimension != expected_dimension:
        msg = (
            f"This workspace's vector database was built with a different embedding model "
            f"(dimension mismatch: stored={stored_dimension}, configured={expected_dimension}). "
            f"Please delete and rebuild the vector database for this workspace before continuing. "
            f"See migration steps in the docs."
        )
        LOGGER.error(msg)
        raise EmbeddingDimensionMismatchError(msg)
