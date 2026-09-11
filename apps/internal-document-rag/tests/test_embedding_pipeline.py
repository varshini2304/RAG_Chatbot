"""Unit tests for Step 5 EmbeddingPipeline orchestrator."""

from __future__ import annotations

import pytest

from app.embeddings.embedding_pipeline import EmbeddingPipeline, EmbeddingPipelineError
from app.embeddings.embedding_service import EmbeddingService
from app.models.schemas import ChunkMetadata, DocumentChunk
from app.vectorstore.chroma_manager import ChromaVectorStore


class FakeEmbeddingModel:

    def __init__(
        self,
        embeddings: list[list[float]] | None = None,
        should_fail: bool = False,
    ) -> None:
        self.embeddings = embeddings or [[0.1, 0.2, 0.3]]
        self.should_fail = should_fail

    def encode(
        self,
        texts: list[str],
        batch_size: int,
        convert_to_numpy: bool,
        show_progress_bar: bool,
    ) -> list[list[float]]:
        if self.should_fail:
            raise RuntimeError("model failure")
        return [self.embeddings[i % len(self.embeddings)] for i in range(len(texts))]


def _chunk(chunk_id: str, content: str = "Policy text") -> DocumentChunk:
    return DocumentChunk(
        content=content,
        metadata=ChunkMetadata(
            source_file="policy.pdf",
            page_number=1,
            chunk_id=chunk_id,
            document_type="pdf",
        ),
    )


def _make_pipeline(
    tmp_path,
    embeddings: list[list[float]] | None = None,
    should_fail_model: bool = False,
    collection_name: str = "test_collection",
) -> tuple[EmbeddingPipeline, ChromaVectorStore]:
    """Build a pipeline wired to a tmp ChromaDB and a fake model."""
    model = FakeEmbeddingModel(embeddings=embeddings, should_fail=should_fail_model)
    # Determine the mock expected dimension to pass to service validation
    mock_embeddings = embeddings or [[0.1, 0.2, 0.3]]
    expected_dim = len(mock_embeddings[0]) if mock_embeddings else 384
    service = EmbeddingService(model=model, expected_dimension=expected_dim)
    store = ChromaVectorStore(
        persist_directory=tmp_path / "chroma",
        collection_name=collection_name,
    )
    pipeline = EmbeddingPipeline(embedding_service=service, vector_store=store)
    return pipeline, store


def test_pipeline_runs_end_to_end(tmp_path) -> None:
    """Full happy path: embeddings generated and persisted to ChromaDB."""
    pipeline, store = _make_pipeline(
        tmp_path,
        embeddings=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
        collection_name="test_pipeline_e2e",
    )
    chunks = [_chunk("policy.pdf-p1-c1"), _chunk("policy.pdf-p1-c2", "More text")]

    ids = pipeline.run(chunks)

    assert ids == ["policy.pdf-p1-c1", "policy.pdf-p1-c2"]
    assert store.collection.count() == 2


def test_pipeline_persists_required_metadata(tmp_path) -> None:
    pipeline, store = _make_pipeline(
        tmp_path,
        embeddings=[[0.1, 0.2, 0.3]],
        collection_name="test_pipeline_metadata",
    )

    pipeline.run([_chunk("policy.pdf-p1-c1")])

    result = store.collection.get(ids=["policy.pdf-p1-c1"], include=["metadatas"])
    metadata = result["metadatas"][0]

    assert metadata["source_file"] == "policy.pdf"
    assert metadata["page_number"] == 1
    assert metadata["chunk_id"] == "policy.pdf-p1-c1"
    assert metadata["document_type"] == "pdf"


def test_pipeline_is_idempotent_on_duplicate_chunks(tmp_path) -> None:
    pipeline, store = _make_pipeline(
        tmp_path,
        embeddings=[[0.1, 0.2, 0.3]],
        collection_name="test_pipeline_idempotent",
    )
    chunks = [_chunk("policy.pdf-p1-c1")]

    pipeline.run(chunks)
    ids = pipeline.run(chunks)  # Second run must succeed silently.

    assert ids == ["policy.pdf-p1-c1"]
    assert store.collection.count() == 1  # Upsert does not duplicate.


def test_pipeline_rejects_empty_chunk_list(tmp_path) -> None:
    """Pipeline must fast-fail on an empty chunk input."""
    pipeline, _ = _make_pipeline(tmp_path, collection_name="test_pipeline_empty")

    with pytest.raises(EmbeddingPipelineError, match="empty chunk list"):
        pipeline.run([])


def test_pipeline_wraps_embedding_service_errors(tmp_path) -> None:
    """EmbeddingServiceError must be re-raised as EmbeddingPipelineError."""
    pipeline, _ = _make_pipeline(
        tmp_path,
        should_fail_model=True,
        collection_name="test_pipeline_embed_err",
    )

    with pytest.raises(EmbeddingPipelineError, match="embedding generation"):
        pipeline.run([_chunk("policy.pdf-p1-c1")])


def test_pipeline_wraps_vector_store_errors(tmp_path, monkeypatch) -> None:
    """VectorStoreError must be re-raised as EmbeddingPipelineError."""
    pipeline, store = _make_pipeline(
        tmp_path,
        embeddings=[[0.1, 0.2, 0.3]],
        collection_name="test_pipeline_store_err",
    )

    def fail_upsert(**kwargs) -> None:
        raise RuntimeError("upsert failed")

    monkeypatch.setattr(store.collection, "upsert", fail_upsert)

    with pytest.raises(EmbeddingPipelineError, match="vector store insertion"):
        pipeline.run([_chunk("policy.pdf-p1-c1")])


def test_pipeline_emits_structured_logs(
    tmp_path, caplog: pytest.LogCaptureFixture
) -> None:
    pipeline, _ = _make_pipeline(
        tmp_path,
        embeddings=[[0.1, 0.2, 0.3]],
        collection_name="test_pipeline_logs",
    )

    with caplog.at_level("INFO"):
        pipeline.run([_chunk("policy.pdf-p1-c1")])

    messages = [record.message for record in caplog.records]
    assert any("Embedding pipeline started" in m for m in messages)
    assert any("embeddings generated" in m for m in messages)
    assert any("Embedding pipeline completed" in m for m in messages)
