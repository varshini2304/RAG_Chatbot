"""Unit tests for the vector embedding generation module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.embeddings.embedding_pipeline import EmbeddingPipeline, EmbeddingPipelineError
from app.embeddings.embedding_service import EmbeddingServiceError
from app.models.schemas import ChunkMetadata, DocumentChunk


@pytest.fixture
def mock_chunks() -> list[DocumentChunk]:
    """Return sample DocumentChunk instances for testing."""
    return [
        DocumentChunk(
            content="Sample text chunk number 1",
            metadata=ChunkMetadata(
                source_file="doc1.pdf",
                page_number=1,
                chunk_id="doc1.pdf-p1-c1",
                document_type="pdf",
            ),
        ),
        DocumentChunk(
            content="Sample text chunk number 2",
            metadata=ChunkMetadata(
                source_file="doc1.pdf",
                page_number=1,
                chunk_id="doc1.pdf-p1-c2",
                document_type="pdf",
            ),
        ),
    ]


def test_embedding_pipeline_generates_vectors(mock_chunks: list[DocumentChunk]) -> None:
    """EmbeddingPipeline should generate floating-point vector arrays for each chunk."""
    mock_service = MagicMock()
    mock_store = MagicMock()
    mock_service.generate_embeddings.return_value = [
        [0.1] * 384,
        [0.2] * 384,
    ]
    mock_store.add_chunks.return_value = ["doc1.pdf-p1-c1", "doc1.pdf-p1-c2"]

    pipeline = EmbeddingPipeline(
        embedding_service=mock_service, vector_store=mock_store
    )
    result = pipeline.run(mock_chunks)

    assert result == ["doc1.pdf-p1-c1", "doc1.pdf-p1-c2"]
    mock_service.generate_embeddings.assert_called_once()
    mock_store.add_chunks.assert_called_once()


def test_embedding_pipeline_rejects_empty_chunk_list() -> None:
    """Passing an empty list of chunks should raise EmbeddingPipelineError."""
    mock_service = MagicMock()
    mock_store = MagicMock()
    pipeline = EmbeddingPipeline(
        embedding_service=mock_service, vector_store=mock_store
    )

    with pytest.raises(EmbeddingPipelineError, match="empty chunk list"):
        pipeline.run([])


def test_embedding_pipeline_handles_service_exceptions(
    mock_chunks: list[DocumentChunk],
) -> None:
    """Service exceptions should be caught and re-raised as EmbeddingPipelineError."""
    mock_service = MagicMock()
    mock_store = MagicMock()
    mock_service.generate_embeddings.side_effect = EmbeddingServiceError(
        "Model loading failed"
    )

    pipeline = EmbeddingPipeline(
        embedding_service=mock_service, vector_store=mock_store
    )

    with pytest.raises(EmbeddingPipelineError):
        pipeline.run(mock_chunks)
