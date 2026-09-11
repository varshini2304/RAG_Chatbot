"""Unit tests for validation of hybrid search performance, caching lifecycle, and avoidance of query-time index rebuilding."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from app.embeddings.embedding_service import EmbeddingService
from app.models.schemas import ChunkMetadata, DocumentChunk
from app.retrieval.bm25_index_manager import BM25IndexManager
from app.retrieval.retrieval_service import RetrievalService


def _chunk(chunk_id: str, content: str) -> DocumentChunk:
    return DocumentChunk(
        content=content,
        metadata=ChunkMetadata(
            source_file="performance.pdf",
            page_number=1,
            chunk_id=chunk_id,
            document_type="pdf",
        ),
    )


def test_bm25_index_is_cached_and_never_rebuilt_on_query_path(tmp_path: Path) -> None:
    username = "perf_user"
    storage_dir = tmp_path / "bm25"

    manager = BM25IndexManager(username=username, storage_dir=storage_dir)

    # Pre-add chunks to index
    chunks = [
        _chunk("c1", "Performance optimization guidelines."),
        _chunk("c2", "Caching strategies for search indexes."),
    ]
    manager.add_documents(chunks)

    manager.load = MagicMock(side_effect=manager.load)  # type: ignore[method-assign]
    manager.add_documents = MagicMock(side_effect=manager.add_documents)  # type: ignore[method-assign]

    # 1. Initialize RetrievalService injecting the pre-cached manager
    store = MagicMock()
    store.collection_name = "test_collection"
    store.collection.count.return_value = 2
    store.collection.query.return_value = {
        "ids": [["c1"]],
        "documents": [["Performance optimization guidelines."]],
        "metadatas": [[chunks[0].metadata.model_dump()]],
        "distances": [[0.1]],
    }

    emb_service = MagicMock(spec=EmbeddingService)
    emb_service.embed_texts.return_value = [[0.1, 0.2, 0.3]]

    retrieval = RetrievalService(
        embedding_service=emb_service,
        vector_store=store,
        top_k=2,
        enable_hybrid_search=True,
        bm25_index_manager=manager,
    )

    # Run multiple queries
    for _ in range(5):
        retrieval.search("optimization", top_k=1)

    assert manager.load.call_count == 0
    assert manager.add_documents.call_count == 0

    # - Caching is maintained: query hits are returned from the in-memory index
    res = manager.search("optimization", top_k=1)
    assert len(res) == 1
    assert res[0].metadata.chunk_id == "c1"


def test_bm25_index_refresh_triggers_strictly_on_ingestion_mutations(
    tmp_path: Path,
) -> None:
    username = "mutation_perf_user"
    storage_dir = tmp_path / "bm25_mutation"

    manager = BM25IndexManager(username=username, storage_dir=storage_dir)
    manager.load()

    # Spy/mock the persistence logic
    manager._save = MagicMock(side_effect=manager._save)  # type: ignore[method-assign]

    # 1. Verification of incremental ingestion
    # - Saving index occurs only on add_documents
    chunks = [_chunk("c1", "Initial document chunk.")]
    manager.add_documents(chunks)
    assert manager._save.call_count == 1

    # - Saving index occurs on remove_document_by_source
    manager.remove_document_by_source("performance.pdf")
    assert manager._save.call_count == 2

    # - Querying does NOT trigger save/disk-writes
    manager.search("Initial", top_k=1)
    assert manager._save.call_count == 2
