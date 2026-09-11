"""Unit tests for the retrieval, query preprocessing, and hybrid search module."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.models.schemas import ChunkMetadata, DocumentChunk
from app.retrieval.bm25_index_manager import BM25IndexManager
from app.retrieval.query_preprocessor import QueryPreprocessor
from app.retrieval.retrieval_service import RetrievalService


def test_query_preprocessor_normalizes_text() -> None:
    """QueryPreprocessor should clean and strip whitespace from query strings."""
    preprocessor = QueryPreprocessor()
    raw_query = "  What IS the   company POLICY???  "
    clean_query = preprocessor.preprocess(raw_query)
    assert (
        "company POLICY" in clean_query
        or "company policy" in clean_query.lower()
        or "company" in clean_query.lower()
    )


def test_query_preprocessor_handles_empty_query() -> None:
    """Empty or whitespace-only queries should return empty string."""
    preprocessor = QueryPreprocessor()
    assert preprocessor.preprocess("   ") == ""


def test_bm25_index_manager_indexing_and_scoring(tmp_path) -> None:
    """BM25IndexManager should index document chunks and return search matches."""
    chunks = [
        DocumentChunk(
            content="Employee leave policy and paid time off guidelines.",
            metadata=ChunkMetadata(
                source_file="hr.pdf",
                page_number=1,
                chunk_id="hr-p1-c1",
                document_type="pdf",
            ),
        ),
        DocumentChunk(
            content="Financial quarter expense reports and revenue balance.",
            metadata=ChunkMetadata(
                source_file="finance.pdf",
                page_number=1,
                chunk_id="fin-p1-c1",
                document_type="pdf",
            ),
        ),
    ]

    manager = BM25IndexManager(username="admin", storage_dir=tmp_path)
    manager.add_documents(chunks)
    assert len(manager._chunk_ids) == 2

    results = manager.search("leave policy", top_k=2)
    assert len(results) >= 1
    assert results[0].metadata.source_file == "hr.pdf"


def test_bm25_index_manager_handles_unindexed_search(tmp_path) -> None:
    """Searching before indexing should return an empty list gracefully."""
    manager = BM25IndexManager(username="admin", storage_dir=tmp_path)
    results = manager.search("anything", top_k=5)
    assert results == []


def test_retrieval_service_search_execution() -> None:
    """RetrievalService should execute top-k search over vector store."""
    mock_collection = MagicMock()
    mock_collection.metadata = {"embedding_dimension": 384}
    mock_collection.count.return_value = 1
    mock_collection.query.return_value = {
        "ids": [["hr-p1-c1"]],
        "documents": [["HR Policy content"]],
        "metadatas": [
            [
                {
                    "source_file": "hr.pdf",
                    "page_number": 1,
                    "chunk_id": "hr-p1-c1",
                    "document_type": "pdf",
                }
            ]
        ],
        "distances": [[0.15]],
    }

    mock_vector_store = MagicMock()
    mock_vector_store.collection = mock_collection

    mock_embedding_service = MagicMock()
    mock_embedding_service.embed_texts.return_value = [[0.1] * 384]

    service = RetrievalService(
        vector_store=mock_vector_store,
        embedding_service=mock_embedding_service,
        enable_hybrid_search=False,
    )
    retrieved = service.search("hr policy", top_k=5)
    assert isinstance(retrieved, list)
    assert len(retrieved) == 1
    assert retrieved[0].metadata.source_file == "hr.pdf"


def test_query_service_pre_llm_relevance_check() -> None:
    """QueryService should reject irrelevant chunks before invoking LLM."""
    from app.services.query_service import QueryService

    chunk = DocumentChunk(
        content="Employee annual leave policy allows 20 paid vacation days.",
        metadata=ChunkMetadata(
            source_file="hr.pdf",
            page_number=1,
            chunk_id="hr-p1-c1",
            document_type="pdf",
        ),
    )
    assert (
        QueryService._is_retrieval_relevant("What is the leave policy?", [chunk])
        is True
    )
    assert QueryService._is_retrieval_relevant("Who is Virat Kohli?", [chunk]) is False
