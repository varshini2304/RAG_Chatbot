"""Unit tests for Step 5 ChromaDB persistence."""

from __future__ import annotations

import pytest

from app.models.schemas import ChunkMetadata, DocumentChunk
from app.vectorstore.chroma_manager import ChromaVectorStore, VectorStoreError


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


def test_vector_store_initializes_persistent_collection(tmp_path) -> None:
    """Vector store should create a local persistent ChromaDB collection."""
    store = ChromaVectorStore(
        persist_directory=tmp_path / "chroma",
        collection_name="test_initialization",
    )

    assert store.persist_directory.exists()
    assert store.collection.name == "test_initialization"


def test_add_chunks_inserts_documents_and_embeddings(tmp_path) -> None:
    """Chunks, embeddings, and text should be inserted into ChromaDB."""
    store = ChromaVectorStore(
        persist_directory=tmp_path / "chroma",
        collection_name="test_document_insertion",
    )
    chunks = [
        _chunk("policy.pdf-p1-c1"),
        _chunk("policy.pdf-p1-c2", "More policy text"),
    ]
    embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

    ids = store.add_chunks(chunks, embeddings)
    stored = store.collection.get(ids=ids, include=["documents", "metadatas"])

    assert ids == ["policy.pdf-p1-c1", "policy.pdf-p1-c2"]
    assert store.collection.count() == 2
    assert stored["documents"] == ["Policy text", "More policy text"]


def test_add_chunks_persists_required_metadata(tmp_path) -> None:
    """Stored Chroma metadata should include all Step 5 required fields."""
    store = ChromaVectorStore(
        persist_directory=tmp_path / "chroma",
        collection_name="test_metadata_persistence",
    )
    chunk = _chunk("policy.pdf-p1-c1")

    store.add_chunks([chunk], [[0.1, 0.2, 0.3]])
    stored = store.collection.get(ids=["policy.pdf-p1-c1"], include=["metadatas"])
    metadata = stored["metadatas"][0]

    assert metadata["source_file"] == "policy.pdf"
    assert metadata["page_number"] == 1
    assert metadata["chunk_id"] == "policy.pdf-p1-c1"
    assert metadata["document_type"] == "pdf"


def test_add_chunks_rejects_embedding_count_mismatch(tmp_path) -> None:
    """Vector store validation should reject chunk and embedding count mismatches."""
    store = ChromaVectorStore(
        persist_directory=tmp_path / "chroma",
        collection_name="test_count_mismatch",
    )

    with pytest.raises(VectorStoreError, match="count must match"):
        store.add_chunks([_chunk("policy.pdf-p1-c1")], [])


def test_add_chunks_rejects_inconsistent_embedding_dimensions(tmp_path) -> None:
    """Vector store validation should reject mixed embedding dimensions."""
    store = ChromaVectorStore(
        persist_directory=tmp_path / "chroma",
        collection_name="test_dimension_validation",
    )
    chunks = [_chunk("policy.pdf-p1-c1"), _chunk("policy.pdf-p1-c2")]

    with pytest.raises(VectorStoreError, match="same dimension"):
        store.add_chunks(chunks, [[0.1, 0.2], [0.3]])


def test_add_chunks_wraps_chromadb_failures(tmp_path, monkeypatch) -> None:
    """ChromaDB upsert failures should be exposed as VectorStoreError."""
    store = ChromaVectorStore(
        persist_directory=tmp_path / "chroma",
        collection_name="test_failure_handling",
    )

    def fail_upsert(**kwargs):
        raise RuntimeError("upsert failed")

    monkeypatch.setattr(store.collection, "upsert", fail_upsert)

    with pytest.raises(VectorStoreError, match="Failed to insert chunks"):
        store.add_chunks([_chunk("policy.pdf-p1-c1")], [[0.1, 0.2, 0.3]])


def test_add_chunks_recovers_when_collection_was_deleted_out_of_band(tmp_path) -> None:
    """Vector store should recreate the collection if a cached handle goes stale."""
    store = ChromaVectorStore(
        persist_directory=tmp_path / "chroma",
        collection_name="test_collection_recovery",
    )

    store.client.delete_collection(store.collection_name)

    ids = store.add_chunks([_chunk("policy.pdf-p1-c1")], [[0.1, 0.2, 0.3]])

    assert ids == ["policy.pdf-p1-c1"]
    assert store.collection.count() == 1


def test_vector_store_emits_logs(tmp_path, caplog: pytest.LogCaptureFixture) -> None:
    """Vector store should log initialization, collection readiness, and upsert."""
    with caplog.at_level("INFO"):
        store = ChromaVectorStore(
            persist_directory=tmp_path / "chroma",
            collection_name="test_logs",
        )
        store.add_chunks([_chunk("policy.pdf-p1-c1")], [[0.1, 0.2, 0.3]])

    messages = [record.message for record in caplog.records]
    assert any("Initializing ChromaDB" in message for message in messages)
    assert any("ChromaDB collection ready" in message for message in messages)
    assert any("Upserted 1 chunks" in message for message in messages)
