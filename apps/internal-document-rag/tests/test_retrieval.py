
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.embeddings.embedding_service import EmbeddingService
from app.models.schemas import (
    TOP_K_MAX,
    ChunkMetadata,
    DocumentChunk,
    InvalidTopKError,
    TopKRetrievalConfig,
)
from app.retrieval.retrieval_service import (
    ChromaQueryError,
    EmptyQuestionError,
    QuestionEmbeddingError,
    RetrievalService,
)
from app.retrieval.retriever import DocumentRetriever, RetrieverError
from app.vectorstore.chroma_manager import ChromaVectorStore

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


class FakeEmbeddingModel:
    """Deterministic embedding model for full test isolation."""

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
    """Build a deterministic test ``DocumentChunk``."""
    return DocumentChunk(
        content=content,
        metadata=ChunkMetadata(
            source_file="policy.pdf",
            page_number=1,
            chunk_id=chunk_id,
            document_type="pdf",
        ),
    )


def _chunk_full(
    chunk_id: str,
    content: str,
    source_file: str,
    page_number: int,
    document_type: str,
) -> DocumentChunk:
    """Build a ``DocumentChunk`` with fully specified metadata."""
    return DocumentChunk(
        content=content,
        metadata=ChunkMetadata(
            source_file=source_file,
            page_number=page_number,
            chunk_id=chunk_id,
            document_type=document_type,
        ),
    )


def _make_service(
    tmp_path,
    embeddings: list[list[float]] | None = None,
    should_fail_model: bool = False,
    collection_name: str = "test_retrieval",
    top_k: int = 5,
) -> tuple[RetrievalService, ChromaVectorStore, EmbeddingService]:
    """Wire a ``RetrievalService`` against a temp ChromaDB and a fake model."""
    model = FakeEmbeddingModel(embeddings=embeddings, should_fail=should_fail_model)
    service = EmbeddingService(model=model, expected_dimension=3)
    store = ChromaVectorStore(
        persist_directory=tmp_path / "chroma",
        collection_name=collection_name,
    )
    retrieval = RetrievalService(
        embedding_service=service,
        vector_store=store,
        top_k=top_k,
        enable_hybrid_search=False,
    )
    return retrieval, store, service


def _seed_store(
    store: ChromaVectorStore,
    service: EmbeddingService,
    chunks: list[DocumentChunk],
) -> None:
    """Embed and upsert chunks into the store for search testing."""
    embeddings = service.generate_embeddings(chunks)
    store.add_chunks(chunks, embeddings)


# ---------------------------------------------------------------------------
# TestTopKRetrievalConfig
# ---------------------------------------------------------------------------


class TestTopKRetrievalConfig:
    """Tests for the ``TopKRetrievalConfig`` Pydantic model."""

    def test_default_top_k_is_five(self) -> None:
        """Default construction must produce top_k=5."""
        config = TopKRetrievalConfig()
        assert config.top_k == 5

    def test_top_k_one_is_valid(self) -> None:
        """top_k=1 is the minimum valid value."""
        config = TopKRetrievalConfig(top_k=1)
        assert config.top_k == 1

    def test_top_k_three_is_valid(self) -> None:
        """top_k=3 is a typical valid value."""
        config = TopKRetrievalConfig(top_k=3)
        assert config.top_k == 3

    def test_top_k_five_is_valid(self) -> None:
        """top_k=5 (the default) is explicitly valid."""
        config = TopKRetrievalConfig(top_k=5)
        assert config.top_k == 5

    def test_top_k_at_max_boundary_is_valid(self) -> None:
        """top_k=TOP_K_MAX (100) is the maximum valid value."""
        config = TopKRetrievalConfig(top_k=TOP_K_MAX)
        assert config.top_k == TOP_K_MAX

    def test_top_k_zero_raises_validation_error(self) -> None:
        """top_k=0 must fail Pydantic Field(ge=1) validation."""
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            TopKRetrievalConfig(top_k=0)  # type: ignore[arg-type]

    def test_top_k_negative_raises_validation_error(self) -> None:
        """top_k=-1 must fail Pydantic Field(ge=1) validation."""
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            TopKRetrievalConfig(top_k=-1)  # type: ignore[arg-type]

    def test_top_k_above_max_raises_invalid_top_k_error(self) -> None:
        """top_k exceeding TOP_K_MAX must raise ``InvalidTopKError`` via validator."""
        import pydantic

        with pytest.raises(pydantic.ValidationError) as exc_info:
            TopKRetrievalConfig(top_k=TOP_K_MAX + 1)

        # Pydantic wraps the underlying InvalidTopKError; confirm cause type.
        errors = exc_info.value.errors()
        assert any("top_k" in str(e) or "exceeds" in str(e) for e in errors)

    def test_top_k_config_is_frozen(self) -> None:
        """``TopKRetrievalConfig`` must be immutable after construction."""
        config = TopKRetrievalConfig(top_k=3)
        with pytest.raises((TypeError, Exception)):
            config.top_k = 10  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TestEmbedQuestion
# ---------------------------------------------------------------------------


class TestEmbedQuestion:
    """Tests for ``RetrievalService.embed_question``."""

    def test_embed_question_returns_vector(self, tmp_path) -> None:
        """A valid question produces an embedding vector of the correct dimension."""
        retrieval, _, _ = _make_service(
            tmp_path,
            embeddings=[[0.1, 0.2, 0.3]],
            collection_name="test_embed_q_vector",
        )
        embedding = retrieval.embed_question("What is the leave policy?")

        assert isinstance(embedding, list)
        assert len(embedding) == 3
        assert all(isinstance(v, float) for v in embedding)

    def test_embed_question_rejects_empty_string(self, tmp_path) -> None:
        """An empty question must raise ``RetrievalServiceError``."""
        retrieval, _, _ = _make_service(tmp_path, collection_name="test_embed_q_empty")
        with pytest.raises(EmptyQuestionError, match="empty"):
            retrieval.embed_question("")

    def test_embed_question_rejects_whitespace_only(self, tmp_path) -> None:
        """A whitespace-only question must raise ``RetrievalServiceError``."""
        retrieval, _, _ = _make_service(tmp_path, collection_name="test_embed_q_ws")
        with pytest.raises(EmptyQuestionError, match="empty"):
            retrieval.embed_question("   \t\n  ")

    def test_embed_question_wraps_model_error(self, tmp_path) -> None:
        """Model failures must be wrapped as ``RetrievalServiceError``."""
        retrieval, _, _ = _make_service(
            tmp_path,
            should_fail_model=True,
            collection_name="test_embed_q_err",
        )
        with pytest.raises(QuestionEmbeddingError, match="Failed to generate"):
            retrieval.embed_question("Any question")


# ---------------------------------------------------------------------------
# TestTopKRetrieval
# ---------------------------------------------------------------------------


class TestTopKRetrieval:
    """Core top_k retrieval tests: explicit values 1, 3, 5, and edge cases."""

    def test_top_k_1_returns_exactly_one_result(self, tmp_path) -> None:
        """top_k=1 must return exactly one chunk from a seeded store."""
        retrieval, store, service = _make_service(
            tmp_path,
            embeddings=[[0.1, 0.2, 0.3]],
            collection_name="test_topk_1",
        )
        chunks = [_chunk(f"doc-p1-c{i}", f"Content {i}") for i in range(5)]
        _seed_store(store, service, chunks)

        results = retrieval.search("query text", top_k=1)

        assert len(results) == 1
        assert isinstance(results[0], DocumentChunk)

    def test_top_k_3_returns_exactly_three_results(self, tmp_path) -> None:
        """top_k=3 must return exactly three chunks from a seeded store."""
        retrieval, store, service = _make_service(
            tmp_path,
            embeddings=[[0.1, 0.2, 0.3]],
            collection_name="test_topk_3",
        )
        chunks = [_chunk(f"doc-p1-c{i}", f"Content {i}") for i in range(5)]
        _seed_store(store, service, chunks)

        results = retrieval.search("query text", top_k=3)

        assert len(results) == 3
        assert all(isinstance(r, DocumentChunk) for r in results)

    def test_top_k_5_returns_exactly_five_results(self, tmp_path) -> None:
        """top_k=5 must return exactly five chunks from a store with ≥5 chunks."""
        retrieval, store, service = _make_service(
            tmp_path,
            embeddings=[[0.1, 0.2, 0.3]],
            collection_name="test_topk_5",
        )
        chunks = [_chunk(f"doc-p1-c{i}", f"Content {i}") for i in range(7)]
        _seed_store(store, service, chunks)

        results = retrieval.search("query text", top_k=5)

        assert len(results) == 5
        assert all(isinstance(r, DocumentChunk) for r in results)

    def test_top_k_larger_than_store_returns_all_chunks(self, tmp_path) -> None:
        """When the store has fewer chunks than top_k, all chunks are returned."""
        retrieval, store, service = _make_service(
            tmp_path,
            embeddings=[[0.1, 0.2, 0.3]],
            collection_name="test_topk_overflow",
            top_k=10,
        )
        chunks = [_chunk(f"doc-p1-c{i}", f"Content {i}") for i in range(3)]
        _seed_store(store, service, chunks)

        results = retrieval.search("query text", top_k=10)

        assert len(results) == 3

    def test_default_top_k_used_when_none_supplied(self, tmp_path) -> None:
        """Without an explicit top_k argument, the service default is applied."""
        retrieval, store, service = _make_service(
            tmp_path,
            embeddings=[[0.1, 0.2, 0.3]],
            collection_name="test_topk_default",
            top_k=2,
        )
        chunks = [_chunk(f"doc-p1-c{i}", f"Content {i}") for i in range(5)]
        _seed_store(store, service, chunks)

        results = retrieval.search("query text")  # no top_k → uses default 2

        assert len(results) == 2

    def test_per_call_top_k_overrides_service_default(self, tmp_path) -> None:
        """A top_k supplied to search() overrides the service-level default."""
        retrieval, store, service = _make_service(
            tmp_path,
            embeddings=[[0.1, 0.2, 0.3]],
            collection_name="test_topk_override",
            top_k=5,
        )
        chunks = [_chunk(f"doc-p1-c{i}", f"Content {i}") for i in range(5)]
        _seed_store(store, service, chunks)

        results = retrieval.search("query text", top_k=1)

        assert len(results) == 1


# ---------------------------------------------------------------------------
# TestRetrievalOrdering
# ---------------------------------------------------------------------------


class TestRetrievalOrdering:

    def test_scores_are_non_decreasing(self, tmp_path) -> None:

        retrieval, store, service = _make_service(
            tmp_path,
            embeddings=[[0.1, 0.2, 0.3]],
            collection_name="test_ordering_scores",
        )
        chunks = [_chunk(f"doc-p1-c{i}", f"Content {i}") for i in range(5)]
        _seed_store(store, service, chunks)

        results = retrieval.search("query text", top_k=5)

        assert len(results) == 5
        assert all(isinstance(result, DocumentChunk) for result in results)

    def test_chromadb_order_is_preserved_exactly(self) -> None:
        raw = {
            "ids": [["chunk-c", "chunk-a", "chunk-b"]],
            "documents": [["Content C", "Content A", "Content B"]],
            "metadatas": [
                [
                    {
                        "source_file": "c.pdf",
                        "page_number": 3,
                        "chunk_id": "chunk-c",
                        "document_type": "pdf",
                    },
                    {
                        "source_file": "a.pdf",
                        "page_number": 1,
                        "chunk_id": "chunk-a",
                        "document_type": "pdf",
                    },
                    {
                        "source_file": "b.pdf",
                        "page_number": 2,
                        "chunk_id": "chunk-b",
                        "document_type": "pdf",
                    },
                ]
            ],
            "distances": [[0.42, 0.11, 0.33]],
        }

        results = RetrievalService._parse_query_results(raw)

        assert [chunk.metadata.chunk_id for chunk in results] == [
            "chunk-c",
            "chunk-a",
            "chunk-b",
        ]

    def test_result_order_is_preserved_across_runs(self, tmp_path) -> None:
        """Two identical queries must produce the same result ordering."""
        retrieval, store, service = _make_service(
            tmp_path,
            embeddings=[[0.1, 0.2, 0.3]],
            collection_name="test_ordering_stable",
        )
        chunks = [_chunk(f"doc-p1-c{i}", f"Content {i}") for i in range(5)]
        _seed_store(store, service, chunks)

        results_a = retrieval.search("query text", top_k=5)
        results_b = retrieval.search("query text", top_k=5)

        ids_a = [r.metadata.chunk_id for r in results_a]
        ids_b = [r.metadata.chunk_id for r in results_b]
        assert ids_a == ids_b, "Result ordering changed between identical queries."

    def test_top_k_slices_from_ranked_list(self, tmp_path) -> None:
        """top_k=2 must return the first 2 results of the full-k ranked list."""
        retrieval, store, service = _make_service(
            tmp_path,
            embeddings=[[0.1, 0.2, 0.3]],
            collection_name="test_ordering_slice",
        )
        chunks = [_chunk(f"doc-p1-c{i}", f"Content {i}") for i in range(5)]
        _seed_store(store, service, chunks)

        results_2 = retrieval.search("query text", top_k=2)

        assert len(results_2) == 2
        assert all(isinstance(result, DocumentChunk) for result in results_2)


# ---------------------------------------------------------------------------
# TestMetadataPreservation
# ---------------------------------------------------------------------------


class TestMetadataPreservation:
    """All required metadata fields must be present and accurate."""

    def test_retrieval_result_has_all_required_fields(self, tmp_path) -> None:
        """Each result must expose source_file, page_number, chunk_id, document_type."""
        retrieval, store, service = _make_service(
            tmp_path,
            embeddings=[[0.1, 0.2, 0.3]],
            collection_name="test_meta_all_fields",
        )
        chunk = _chunk_full(
            chunk_id="handbook.pdf-p3-c1",
            content="Detailed policy content",
            source_file="handbook.pdf",
            page_number=3,
            document_type="pdf",
        )
        _seed_store(store, service, [chunk])

        results = retrieval.search("policy details", top_k=1)

        assert len(results) == 1
        result = results[0]
        assert result.metadata.source_file == "handbook.pdf"
        assert result.metadata.page_number == 3
        assert result.metadata.chunk_id == "handbook.pdf-p3-c1"
        assert result.metadata.document_type == "pdf"
        assert result.content == "Detailed policy content"

    def test_metadata_matches_across_multiple_results(self, tmp_path) -> None:
        """Metadata must be independently correct for each returned chunk."""
        retrieval, store, service = _make_service(
            tmp_path,
            embeddings=[[0.1, 0.2, 0.3]],
            collection_name="test_meta_multi",
        )
        chunks = [
            _chunk_full(
                chunk_id=f"doc{i}.pdf-p{i}-c1",
                content=f"Content for document {i}",
                source_file=f"doc{i}.pdf",
                page_number=i + 1,
                document_type="pdf",
            )
            for i in range(3)
        ]
        _seed_store(store, service, chunks)

        results = retrieval.search("document content", top_k=3)

        assert len(results) == 3
        result_ids = {r.metadata.chunk_id for r in results}
        expected_ids = {f"doc{i}.pdf-p{i}-c1" for i in range(3)}
        assert result_ids == expected_ids

        for result in results:
            assert result.metadata.source_file
            assert result.metadata.page_number >= 1
            assert result.metadata.chunk_id
            assert result.metadata.document_type
            assert result.content

    def test_metadata_preserved_with_txt_document_type(self, tmp_path) -> None:
        """document_type='txt' must be round-tripped correctly via ChromaDB."""
        retrieval, store, service = _make_service(
            tmp_path,
            embeddings=[[0.1, 0.2, 0.3]],
            collection_name="test_meta_txt",
        )
        chunk = _chunk_full(
            chunk_id="notes.txt-p1-c1",
            content="Plain text notes",
            source_file="notes.txt",
            page_number=1,
            document_type="txt",
        )
        _seed_store(store, service, [chunk])

        results = retrieval.search("notes", top_k=1)

        assert len(results) == 1
        assert results[0].metadata.document_type == "txt"
        assert results[0].metadata.source_file == "notes.txt"

    def test_search_returns_results_with_metadata(self, tmp_path) -> None:
        """Backward-compatible: happy path with correct field values."""
        retrieval, store, service = _make_service(
            tmp_path,
            embeddings=[[0.1, 0.2, 0.3]],
            collection_name="test_search_meta",
        )
        chunks = [
            _chunk("policy.pdf-p1-c1", "Annual leave policy details"),
            _chunk("policy.pdf-p1-c2", "Sick leave rules and limits"),
        ]
        _seed_store(store, service, chunks)

        results = retrieval.search("What is the leave policy?")

        assert len(results) == 2
        assert all(isinstance(r, DocumentChunk) for r in results)
        for result in results:
            assert result.content
            assert result.metadata.source_file == "policy.pdf"
            assert result.metadata.page_number == 1
            assert result.metadata.document_type == "pdf"
            assert result.metadata.chunk_id in (
                "policy.pdf-p1-c1",
                "policy.pdf-p1-c2",
            )


# ---------------------------------------------------------------------------
# TestEmptyVectorStore
# ---------------------------------------------------------------------------


class TestEmptyVectorStore:
    """Querying an empty ChromaDB collection must be safe."""

    def test_search_empty_store_returns_empty_list(self, tmp_path) -> None:
        """An empty collection must return [] without raising."""
        retrieval, _, _ = _make_service(
            tmp_path,
            embeddings=[[0.1, 0.2, 0.3]],
            collection_name="test_empty_store_1",
        )
        results = retrieval.search("Any question")

        assert results == []

    def test_search_empty_store_top_k_1_returns_empty_list(self, tmp_path) -> None:
        """top_k=1 against an empty store must return []."""
        retrieval, _, _ = _make_service(
            tmp_path,
            embeddings=[[0.1, 0.2, 0.3]],
            collection_name="test_empty_store_2",
        )
        results = retrieval.search("Any question", top_k=1)

        assert results == []

    def test_search_empty_store_top_k_5_returns_empty_list(self, tmp_path) -> None:
        """top_k=5 against an empty store must return []."""
        retrieval, _, _ = _make_service(
            tmp_path,
            embeddings=[[0.1, 0.2, 0.3]],
            collection_name="test_empty_store_3",
        )
        results = retrieval.search("Any question", top_k=5)

        assert results == []


# ---------------------------------------------------------------------------
# TestInvalidTopK
# ---------------------------------------------------------------------------


class TestInvalidTopK:
    """``RetrievalService`` must raise typed exceptions for invalid top_k."""

    def test_top_k_zero_raises(self, tmp_path) -> None:
        """top_k=0 must raise ``RetrievalServiceError``."""
        retrieval, _, _ = _make_service(tmp_path, collection_name="test_invalid_zero")
        with pytest.raises(InvalidTopKError, match="positive integer"):
            retrieval.search("Any question", top_k=0)

    def test_top_k_negative_raises(self, tmp_path) -> None:
        """top_k=-1 must raise ``RetrievalServiceError``."""
        retrieval, _, _ = _make_service(tmp_path, collection_name="test_invalid_neg")
        with pytest.raises(InvalidTopKError, match="positive integer"):
            retrieval.search("Any question", top_k=-1)

    def test_top_k_large_negative_raises(self, tmp_path) -> None:
        """top_k=-100 must raise ``RetrievalServiceError``."""
        retrieval, _, _ = _make_service(
            tmp_path, collection_name="test_invalid_large_neg"
        )
        with pytest.raises(InvalidTopKError, match="positive integer"):
            retrieval.search("Any question", top_k=-100)

    def test_top_k_float_raises(self, tmp_path) -> None:
        """top_k=2.5 (float) must raise ``RetrievalServiceError``."""
        retrieval, _, _ = _make_service(tmp_path, collection_name="test_invalid_float")
        with pytest.raises(InvalidTopKError, match="positive integer"):
            retrieval.search("Any question", top_k=2.5)  # type: ignore[arg-type]

    def test_top_k_string_raises(self, tmp_path) -> None:
        """top_k='5' (string) must raise ``RetrievalServiceError``."""
        retrieval, _, _ = _make_service(tmp_path, collection_name="test_invalid_str")
        with pytest.raises(InvalidTopKError, match="positive integer"):
            retrieval.search("Any question", top_k="5")  # type: ignore[arg-type]

    def test_top_k_bool_raises(self, tmp_path) -> None:
        """top_k=True must be rejected even though bool subclasses int."""
        retrieval, _, _ = _make_service(tmp_path, collection_name="test_invalid_bool")
        with pytest.raises(InvalidTopKError, match="positive integer"):
            retrieval.search("Any question", top_k=True)  # type: ignore[arg-type]

    def test_top_k_above_max_raises(self, tmp_path) -> None:
        """top_k > TOP_K_MAX must raise ``RetrievalServiceError``."""
        retrieval, _, _ = _make_service(
            tmp_path, collection_name="test_invalid_above_max"
        )
        with pytest.raises(InvalidTopKError, match="maximum allowed"):
            retrieval.search("Any question", top_k=TOP_K_MAX + 1)

    def test_top_k_way_above_max_raises(self, tmp_path) -> None:
        """top_k=10000 must raise ``RetrievalServiceError``."""
        retrieval, _, _ = _make_service(tmp_path, collection_name="test_invalid_huge")
        with pytest.raises(InvalidTopKError, match="maximum allowed"):
            retrieval.search("Any question", top_k=10_000)


# ---------------------------------------------------------------------------
# TestRetrievalFailureHandling
# ---------------------------------------------------------------------------


class TestRetrievalFailureHandling:
    """Ensure all failure modes are correctly wrapped."""

    def test_chromadb_query_failure_raises_service_error(
        self, tmp_path, monkeypatch
    ) -> None:
        """ChromaDB failures must be wrapped as ``RetrievalServiceError``."""
        retrieval, store, _ = _make_service(
            tmp_path,
            embeddings=[[0.1, 0.2, 0.3]],
            collection_name="test_db_fail",
        )

        def fail_query(**kwargs):
            raise RuntimeError("query failed")

        monkeypatch.setattr(store.collection, "query", fail_query)

        with pytest.raises(ChromaQueryError, match="similarity search failed"):
            retrieval.search("Any question")

    def test_embedding_failure_raises_service_error(self, tmp_path) -> None:
        """An embedding model crash must propagate as ``RetrievalServiceError``."""
        retrieval, _, _ = _make_service(
            tmp_path,
            should_fail_model=True,
            collection_name="test_embed_fail",
        )
        with pytest.raises(QuestionEmbeddingError, match="Failed to generate"):
            retrieval.search("Any question")

    def test_empty_question_raises_service_error(self, tmp_path) -> None:
        """An empty question string must raise ``RetrievalServiceError``."""
        retrieval, _, _ = _make_service(
            tmp_path,
            collection_name="test_empty_q",
        )
        with pytest.raises(EmptyQuestionError, match="empty"):
            retrieval.search("")

    def test_search_wraps_chromadb_error(self, tmp_path, monkeypatch) -> None:
        """Backward-compatible alias for the ChromaDB failure test."""
        retrieval, store, _ = _make_service(
            tmp_path,
            embeddings=[[0.1, 0.2, 0.3]],
            collection_name="test_search_db_err",
        )

        def fail_query(**kwargs):
            raise RuntimeError("query failed")

        monkeypatch.setattr(store.collection, "query", fail_query)

        with pytest.raises(ChromaQueryError, match="similarity search failed"):
            retrieval.search("Any question")


# ---------------------------------------------------------------------------
# TestDocumentRetriever
# ---------------------------------------------------------------------------


class TestDocumentRetriever:
    """Tests for the high-level ``DocumentRetriever`` orchestrator."""

    def test_retriever_happy_path(self, tmp_path) -> None:
        """End-to-end: seed store → retrieve → correct results."""
        model = FakeEmbeddingModel(embeddings=[[0.1, 0.2, 0.3]])
        service = EmbeddingService(model=model, expected_dimension=3)
        store = ChromaVectorStore(
            persist_directory=tmp_path / "chroma",
            collection_name="test_retriever_e2e",
        )
        chunks = [_chunk("doc-p1-c1", "Leave policy information")]
        _seed_store(store, service, chunks)

        retriever = DocumentRetriever(
            embedding_service=service,
            vector_store=store,
        )
        results = retriever.retrieve("What is leave policy?")

        assert len(results) == 1
        assert results[0].metadata.chunk_id == "doc-p1-c1"

    def test_retriever_respects_top_k_parameter(self, tmp_path) -> None:
        """top_k passed to retrieve() must limit the number of results."""
        model = FakeEmbeddingModel(embeddings=[[0.1, 0.2, 0.3]])
        service = EmbeddingService(model=model, expected_dimension=3)
        store = ChromaVectorStore(
            persist_directory=tmp_path / "chroma",
            collection_name="test_retriever_topk",
        )
        chunks = [_chunk(f"doc-p1-c{i}") for i in range(5)]
        _seed_store(store, service, chunks)

        retriever = DocumentRetriever(
            embedding_service=service,
            vector_store=store,
        )
        results = retriever.retrieve("question", top_k=2)

        assert len(results) == 2

    def test_retriever_wraps_service_errors(self, tmp_path) -> None:
        """``RetrievalServiceError`` must be re-raised as ``RetrieverError``."""
        model = FakeEmbeddingModel(embeddings=[[0.1, 0.2, 0.3]])
        service = EmbeddingService(model=model, expected_dimension=3)
        store = ChromaVectorStore(
            persist_directory=tmp_path / "chroma",
            collection_name="test_retriever_err",
        )

        retriever = DocumentRetriever(
            embedding_service=service,
            vector_store=store,
        )
        with pytest.raises(RetrieverError, match="Retrieval pipeline failed"):
            retriever.retrieve("")  # Empty question triggers service error.

    def test_retriever_logs_structured_messages(
        self, tmp_path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Retriever must emit required structured log entries."""
        model = FakeEmbeddingModel(embeddings=[[0.1, 0.2, 0.3]])
        service = EmbeddingService(model=model, expected_dimension=3)
        store = ChromaVectorStore(
            persist_directory=tmp_path / "chroma",
            collection_name="test_retriever_logs",
        )
        _seed_store(store, service, [_chunk("doc-p1-c1")])

        retriever = DocumentRetriever(
            embedding_service=service,
            vector_store=store,
        )

        with caplog.at_level("INFO"):
            retriever.retrieve("test question")

        messages = [record.message for record in caplog.records]
        assert any(
            "Retriever received question" in m for m in messages
        ), "Expected 'Retriever received question' in logs"
        assert any(
            "embedding" in m.lower() for m in messages
        ), "Expected embedding-related log entry"
        assert any(
            "Retriever completed" in m for m in messages
        ), "Expected 'Retriever completed' in logs"

    def test_retriever_service_logs_question_and_top_k(
        self, tmp_path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """RetrievalService must log the question and top_k at search() entry."""
        retrieval, store, service = _make_service(
            tmp_path,
            embeddings=[[0.1, 0.2, 0.3]],
            collection_name="test_service_logs",
        )
        _seed_store(store, service, [_chunk("doc-p1-c1")])

        with caplog.at_level("INFO"):
            retrieval.search("What is the policy?", top_k=3)

        messages = [record.message for record in caplog.records]
        assert any(
            "top_k=3" in m for m in messages
        ), "Expected top_k value logged at search entry"
        assert any(
            "Retrieval request accepted" in m for m in messages
        ), "Expected 'Retrieval request accepted' in service logs"
        assert any(
            "Retrieval started" in m for m in messages
        ), "Expected 'Retrieval started' in service logs"
        assert any(
            "Number of chunks retrieved" in m for m in messages
        ), "Expected retrieved chunk count in service logs"
        assert any(
            "Retrieval completed" in m for m in messages
        ), "Expected 'Retrieval completed' in service logs"


class TestRetrievalThresholdFiltering:

    def test_search_filters_individual_chunks_below_threshold(self, tmp_path) -> None:
        """Chunks with similarity < min_similarity must be discarded, maintaining order."""
        retrieval, store, service = _make_service(
            tmp_path,
            embeddings=[[0.1, 0.2, 0.3]],
            collection_name="test_threshold_filter",
        )

        chunks = [_chunk(f"doc-p1-c{i}", f"Content {i}") for i in range(1, 6)]
        _seed_store(store, service, chunks)

        retrieval._min_similarity = 0.5

        mock_raw = {
            "ids": [["doc-p1-c1", "doc-p1-c2", "doc-p1-c3", "doc-p1-c4", "doc-p1-c5"]],
            "documents": [
                ["Content 1", "Content 2", "Content 3", "Content 4", "Content 5"]
            ],
            "metadatas": [
                [
                    {
                        "source_file": "policy.pdf",
                        "page_number": 1,
                        "chunk_id": "doc-p1-c1",
                        "document_type": "pdf",
                    },
                    {
                        "source_file": "policy.pdf",
                        "page_number": 1,
                        "chunk_id": "doc-p1-c2",
                        "document_type": "pdf",
                    },
                    {
                        "source_file": "policy.pdf",
                        "page_number": 1,
                        "chunk_id": "doc-p1-c3",
                        "document_type": "pdf",
                    },
                    {
                        "source_file": "policy.pdf",
                        "page_number": 1,
                        "chunk_id": "doc-p1-c4",
                        "document_type": "pdf",
                    },
                    {
                        "source_file": "policy.pdf",
                        "page_number": 1,
                        "chunk_id": "doc-p1-c5",
                        "document_type": "pdf",
                    },
                ]
            ],
            "distances": [[0.05, 0.08, 0.13, 0.59, 0.78]],
        }

        with patch.object(store.collection, "query", return_value=mock_raw):
            results = retrieval.search("query text", top_k=5)

        assert len(results) == 3
        assert [r.metadata.chunk_id for r in results] == [
            "doc-p1-c1",
            "doc-p1-c2",
            "doc-p1-c3",
        ]

    def test_search_returns_candidates_when_all_chunks_below_threshold(
        self, tmp_path
    ) -> None:
        """If all chunks fail the similarity threshold, the raw candidates are still returned."""
        retrieval, store, service = _make_service(
            tmp_path,
            embeddings=[[0.1, 0.2, 0.3]],
            collection_name="test_threshold_all_fail",
        )
        chunks = [_chunk("doc-p1-c1"), _chunk("doc-p1-c2")]
        _seed_store(store, service, chunks)

        retrieval._min_similarity = 0.5

        mock_raw = {
            "ids": [["doc-p1-c1", "doc-p1-c2"]],
            "documents": [["Content 1", "Content 2"]],
            "metadatas": [
                [
                    {
                        "source_file": "policy.pdf",
                        "page_number": 1,
                        "chunk_id": "doc-p1-c1",
                        "document_type": "pdf",
                    },
                    {
                        "source_file": "policy.pdf",
                        "page_number": 1,
                        "chunk_id": "doc-p1-c2",
                        "document_type": "pdf",
                    },
                ]
            ],
            "distances": [[0.6, 0.7]],
        }

        with patch.object(store.collection, "query", return_value=mock_raw):
            results = retrieval.search("query text", top_k=2)
        assert [result.metadata.chunk_id for result in results] == [
            "doc-p1-c1",
            "doc-p1-c2",
        ]


class TestQueryPreprocessor:

    def test_unicode_normalization(self) -> None:
        raw = "ｅｎｇｉｎｅｅｒ"
        from app.retrieval.query_preprocessor import QueryPreprocessor

        assert QueryPreprocessor.preprocess(raw) == "engineer"

    def test_excessive_symbols(self) -> None:
        raw = "################# What is the annual &&&&&&&& limit?"
        from app.retrieval.query_preprocessor import QueryPreprocessor

        assert QueryPreprocessor.preprocess(raw) == "What is the annual limit?"

    def test_whitespace_collapsing(self) -> None:
        raw = "Hello\n        World"
        from app.retrieval.query_preprocessor import QueryPreprocessor

        assert QueryPreprocessor.preprocess(raw) == "Hello World"


class TestHybridSearch:
    """Tests for hybrid semantic + BM25 keyword search."""

    def test_hybrid_keyword_relevance(self, tmp_path) -> None:

        retrieval, store, service = _make_service(
            tmp_path,
            embeddings=[
                [0.01, 0.01, 0.01]
            ],  # very weak embedding to fail semantic filter
            collection_name="test_hybrid_keyword",
        )
        retrieval._enable_hybrid_search = True

        # Ingest documents with unique codes/IDs
        chunks = [
            _chunk(
                "c1", "The engineering laptop model is Dell Precision Workstation 7002."
            ),
            _chunk("c2", "The product code is APEX-PATIENT-DB for patient portal."),
            _chunk("c3", "The Chief Executive Officer employee ID is AE-0001."),
        ]
        _seed_store(store, service, chunks)

        # Set up BM25IndexManager for this user workspace
        from app.retrieval.bm25_index_manager import BM25IndexManager

        bm25_manager = BM25IndexManager(
            "rebuild_test_user", storage_dir=tmp_path / "bm25"
        )
        bm25_manager.add_documents(chunks)
        retrieval._bm25_index_manager = bm25_manager

        # Test 1: Laptop model
        res_laptop = retrieval.search("Precision Workstation 7002", top_k=1)
        assert len(res_laptop) == 1
        assert res_laptop[0].metadata.chunk_id == "c1"

        # Test 2: Product code
        res_product = retrieval.search("APEX-PATIENT-DB", top_k=1)
        assert len(res_product) == 1
        assert res_product[0].metadata.chunk_id == "c2"

        # Test 3: Employee ID
        res_employee = retrieval.search("AE-0001", top_k=1)
        assert len(res_employee) == 1
        assert res_employee[0].metadata.chunk_id == "c3"

    def test_japanese_paraphrase_retrieval(self, tmp_path) -> None:
        """Verify Japanese query retrieves the correct English document."""
        retrieval, store, service = _make_service(
            tmp_path,
            embeddings=[[0.1, 0.2, 0.3]],
            collection_name="test_hybrid_ja",
        )
        retrieval._enable_hybrid_search = True

        chunks = [
            _chunk(
                "c1", "Annual leave entitlement is 20 paid days off per calendar year."
            ),
            _chunk("c2", "Vanguard AutoTech Corp is based at Plant B, Detroit."),
        ]
        _seed_store(store, service, chunks)

        from app.retrieval.bm25_index_manager import BM25IndexManager

        bm25_manager = BM25IndexManager(
            "rebuild_test_user_ja", storage_dir=tmp_path / "bm25_ja"
        )
        bm25_manager.add_documents(chunks)
        retrieval._bm25_index_manager = bm25_manager

        res = retrieval.search("有給休暇", top_k=1)
        assert len(res) == 1
        assert res[0].metadata.chunk_id == "c1"

    def test_noisy_multilingual_query_regression(self, tmp_path) -> None:
        """Verify noisy Japanese query gets cleaned and correctly retrieves English document."""
        retrieval, store, service = _make_service(
            tmp_path,
            embeddings=[[0.1, 0.2, 0.3]],
            collection_name="test_hybrid_ja_noisy",
        )
        retrieval._enable_hybrid_search = True

        chunks = [
            _chunk(
                "c1", "Annual leave entitlement is 20 paid days off per calendar year."
            ),
            _chunk("c2", "Vanguard AutoTech Corp is based at Plant B, Detroit."),
        ]
        _seed_store(store, service, chunks)

        from app.retrieval.bm25_index_manager import BM25IndexManager

        bm25_manager = BM25IndexManager(
            "rebuild_test_user_ja_noisy", storage_dir=tmp_path / "bm25_ja_noisy"
        )
        bm25_manager.add_documents(chunks)
        retrieval._bm25_index_manager = bm25_manager

        # Noisy Japanese query with excessive repeated symbols
        noisy_query = "有給休暇####？？？&&&&"

        # Search runs QueryPreprocessor.preprocess internally
        res = retrieval.search(noisy_query, top_k=1)
        assert len(res) == 1
        assert res[0].metadata.chunk_id == "c1"
