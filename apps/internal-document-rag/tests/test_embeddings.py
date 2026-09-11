"""Unit tests for Step 5 embedding generation."""

from __future__ import annotations

import pytest

from app.embeddings.embedding_service import EmbeddingService, EmbeddingServiceError
from app.models.schemas import ChunkMetadata, DocumentChunk


class FakeEmbeddingModel:
    """Small test double for SentenceTransformer."""

    def __init__(
        self, embeddings: list[list[float]] | None = None, should_fail: bool = False
    ):
        self.embeddings = embeddings or [[0.1, 0.2, 0.3]]
        self.should_fail = should_fail
        self.calls: list[dict[str, object]] = []

    def encode(self, texts, batch_size, convert_to_numpy, show_progress_bar):
        self.calls.append(
            {
                "texts": texts,
                "batch_size": batch_size,
                "convert_to_numpy": convert_to_numpy,
                "show_progress_bar": show_progress_bar,
            }
        )
        if self.should_fail:
            raise RuntimeError("model failure")
        return self.embeddings


def _chunk(
    chunk_id: str = "policy.pdf-p1-c1", content: str = "Policy content"
) -> DocumentChunk:
    return DocumentChunk(
        content=content,
        metadata=ChunkMetadata(
            source_file="policy.pdf",
            page_number=1,
            chunk_id=chunk_id,
            document_type="pdf",
        ),
    )


def test_generate_embeddings_returns_one_vector_per_chunk() -> None:
    """Embedding service should generate and validate vectors for every chunk."""
    model = FakeEmbeddingModel(embeddings=[[0.1, 0.2], [0.3, 0.4]])
    service = EmbeddingService(model=model, batch_size=2, expected_dimension=2)
    chunks = [_chunk("policy.pdf-p1-c1"), _chunk("policy.pdf-p1-c2")]

    embeddings = service.generate_embeddings(chunks)

    assert embeddings == [
        [0.4472135954999579, 0.8944271909999159],
        [0.6, 0.8],
    ]
    assert model.calls[0]["texts"] == ["Policy content", "Policy content"]
    assert model.calls[0]["batch_size"] == 2
    assert model.calls[0]["convert_to_numpy"] is True


def test_generate_embeddings_preserves_multilingual_text_input() -> None:
    """Embedding service should pass multilingual content through unchanged."""
    model = FakeEmbeddingModel(embeddings=[[0.1, 0.2]])
    service = EmbeddingService(model=model, batch_size=1, expected_dimension=2)
    chunks = [_chunk(content="これは日本語の文書です。")]

    embeddings = service.generate_embeddings(chunks)

    assert embeddings == [[0.4472135954999579, 0.8944271909999159]]
    assert model.calls[0]["texts"] == ["これは日本語の文書です。"]


def test_generate_embeddings_rejects_empty_chunk_list() -> None:
    """Embedding generation should fail fast for empty input."""
    service = EmbeddingService(model=FakeEmbeddingModel(), expected_dimension=3)

    with pytest.raises(EmbeddingServiceError, match="empty chunk list"):
        service.generate_embeddings([])


def test_generate_embeddings_rejects_count_mismatch() -> None:
    """Embedding count must match chunk count."""
    service = EmbeddingService(
        model=FakeEmbeddingModel(embeddings=[[0.1, 0.2]]), expected_dimension=2
    )
    chunks = [_chunk("policy.pdf-p1-c1"), _chunk("policy.pdf-p1-c2")]

    with pytest.raises(EmbeddingServiceError, match="count must match"):
        service.generate_embeddings(chunks)


def test_generate_embeddings_rejects_inconsistent_dimensions() -> None:
    """All vectors in a batch should have the same dimension."""
    service = EmbeddingService(
        model=FakeEmbeddingModel(embeddings=[[0.1, 0.2], [0.3]]), expected_dimension=2
    )
    chunks = [_chunk("policy.pdf-p1-c1"), _chunk("policy.pdf-p1-c2")]

    with pytest.raises(EmbeddingServiceError, match="same dimension"):
        service.generate_embeddings(chunks)


def test_generate_embeddings_wraps_model_failures() -> None:
    """Model exceptions should be wrapped in an embedding service error."""
    service = EmbeddingService(
        model=FakeEmbeddingModel(should_fail=True), expected_dimension=3
    )

    with pytest.raises(EmbeddingServiceError, match="Failed to generate embeddings"):
        service.generate_embeddings([_chunk()])


def test_embedding_service_emits_logs(caplog: pytest.LogCaptureFixture) -> None:
    """Embedding generation should log batch start and completion."""
    service = EmbeddingService(
        model=FakeEmbeddingModel(embeddings=[[0.1, 0.2]]), expected_dimension=2
    )

    with caplog.at_level("INFO"):
        service.generate_embeddings([_chunk()])

    messages = [record.message for record in caplog.records]
    assert any("Generating embeddings" in message for message in messages)
    assert any("Generated 1 embeddings" in message for message in messages)


def test_embedding_service_rejects_zero_batch_size() -> None:
    """EmbeddingService must raise immediately when batch_size is not positive."""
    with pytest.raises(
        EmbeddingServiceError, match="batch_size must be greater than zero"
    ):
        EmbeddingService(model=FakeEmbeddingModel(), batch_size=0)
