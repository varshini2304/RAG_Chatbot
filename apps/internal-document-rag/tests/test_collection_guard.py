"""Unit tests for collection dimension guard check."""

from __future__ import annotations

import pytest

from app.vectorstore.collection_guard import (
    EmbeddingDimensionMismatchError,
    assert_collection_dimension_matches,
)


class MockCollection:
    """Mock Chroma collection class for guard tests."""

    def __init__(
        self, name: str, metadata: dict | None = None, embeddings: list | None = None
    ) -> None:
        self.name = name
        self.metadata = metadata
        self._embeddings = embeddings or []

    def get(self, limit: int = 1, include: list | None = None) -> dict:
        if include and "embeddings" in include and self._embeddings:
            return {"embeddings": [self._embeddings[0]]}
        return {}


def test_assert_collection_dimension_matches_with_metadata() -> None:
    # 1. Metadata matches
    col = MockCollection("test_col", metadata={"embedding_dimension": 1024})
    assert_collection_dimension_matches(
        col, expected_dimension=1024
    )  # Should not raise

    # 2. Metadata mismatches
    col_wrong = MockCollection("test_col_wrong", metadata={"embedding_dimension": 384})
    with pytest.raises(EmbeddingDimensionMismatchError) as exc_info:
        assert_collection_dimension_matches(col_wrong, expected_dimension=1024)

    assert "dimension mismatch: stored=384, configured=1024" in str(exc_info.value)


def test_assert_collection_dimension_matches_fallback_to_vector() -> None:
    # 1. No metadata, but has vectors of length 384
    col_legacy = MockCollection("test_legacy", metadata=None, embeddings=[[0.1] * 384])

    # Matches 384
    assert_collection_dimension_matches(col_legacy, expected_dimension=384)

    # Mismatches 1024
    with pytest.raises(EmbeddingDimensionMismatchError) as exc_info:
        assert_collection_dimension_matches(col_legacy, expected_dimension=1024)
    assert "dimension mismatch: stored=384, configured=1024" in str(exc_info.value)


def test_assert_collection_dimension_matches_empty_and_no_metadata() -> None:
    # Empty legacy collection
    col_empty = MockCollection("test_empty", metadata=None, embeddings=[])

    # Should not raise since dimension cannot be determined (assumes matching/empty)
    assert_collection_dimension_matches(col_empty, expected_dimension=1024)
