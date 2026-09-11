"""Unit and integration tests for hybrid search logic, reciprocal rank fusion (RRF), and fail-safes."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from app.config import settings as app_settings
from app.models.schemas import ChunkMetadata, DocumentChunk
from app.retrieval.bm25_index_manager import BM25IndexManager
from app.retrieval.retrieval_service import RetrievalService
from app.vectorstore.chroma_manager import ChromaVectorStore


@contextmanager
def override_settings(**kwargs):
    """Context manager to temporarily override global Settings singleton values."""
    originals = {k: getattr(app_settings, k) for k in kwargs}
    try:
        for k, v in kwargs.items():
            object.__setattr__(app_settings, k, v)
        yield
    finally:
        for k, v in originals.items():
            object.__setattr__(app_settings, k, v)


class FakeEmbeddingModel:
    """Mock model to return deterministic embedding vectors."""

    def __init__(self, embeddings: list[list[float]] | None = None) -> None:
        self.embeddings = embeddings or [[0.1, 0.2, 0.3]]
        self._mapping: dict[str, list[float]] = {}

    def encode(self, texts: list[str], *args, **kwargs) -> list[list[float]]:
        generated = [
            self.embeddings[i % len(self.embeddings)] for i in range(len(texts))
        ]

        if len(texts) > 1:
            for text, emb in zip(texts, generated):
                self._mapping[text] = emb

        res = []
        for text in texts:
            if text in self._mapping:
                res.append(self._mapping[text])
            else:
                # Find the key with the highest token/character overlap
                best_key = None
                best_score = -1.0

                import re

                words_text = {w.lower() for w in re.split(r"\W+", text) if w}
                chars_text = {c.lower() for c in text if c.isalnum()}

                for key in self._mapping:
                    words_key = {w.lower() for w in re.split(r"\W+", key) if w}
                    chars_key = {c.lower() for c in key if c.isalnum()}

                    word_overlap = len(words_text & words_key)
                    char_overlap = len(chars_text & chars_key)
                    score = word_overlap * 10.0 + char_overlap

                    if score > best_score:
                        best_score = score
                        best_key = key

                if best_key is not None and best_score > 0:
                    res.append(self._mapping[best_key])
                else:
                    idx = texts.index(text)
                    res.append(generated[idx])
        return res


def _chunk(chunk_id: str, content: str) -> DocumentChunk:
    return DocumentChunk(
        content=content,
        metadata=ChunkMetadata(
            source_file="policy.pdf",
            page_number=1,
            chunk_id=chunk_id,
            document_type="pdf",
        ),
    )


def _seed_store_and_bm25(
    tmp_path: Path,
    chunks: list[DocumentChunk],
    embeddings: list[list[float]],
    username: str = "hybrid_user",
) -> tuple[RetrievalService, BM25IndexManager]:
    """Helper to initialize VectorStore and BM25 manager with test chunks."""
    model = FakeEmbeddingModel(embeddings=embeddings)

    with override_settings(embedding_dimension=3):
        from app.embeddings.embedding_service import EmbeddingService

        service = EmbeddingService(model=model, expected_dimension=3)

        store = ChromaVectorStore(
            persist_directory=tmp_path / "chroma",
            collection_name=f"test_collection_{username}",
        )

        ids = [c.metadata.chunk_id for c in chunks]
        texts = [c.content for c in chunks]
        metadatas = [c.metadata.to_chroma_dict() for c in chunks]

        # Generate vectors
        vectors = service.embed_texts(texts)

        # Insert
        store.collection.add(
            ids=ids,
            embeddings=vectors,
            metadatas=metadatas,
            documents=texts,
        )

        # BM25 manager setup
        bm25 = BM25IndexManager(
            username=username, storage_dir=tmp_path / "bm25" / username
        )
        bm25.add_documents(chunks)

        retrieval = RetrievalService(
            embedding_service=service,
            vector_store=store,
            top_k=5,
            enable_hybrid_search=True,
            bm25_index_manager=bm25,
        )
        return retrieval, bm25


def test_semantic_only_search(tmp_path: Path) -> None:
    # 1. Setup chunks and disable hybrid search explicitly
    chunks = [
        _chunk("c1", "Annual leave policy rules."),
        _chunk("c2", "Detroit factory layout."),
    ]
    retrieval, _bm25 = _seed_store_and_bm25(
        tmp_path,
        chunks,
        embeddings=[[0.8, 0.1, 0.1], [0.1, 0.8, 0.1]],
        username="sem_only",
    )
    retrieval._enable_hybrid_search = False

    # Run query with min similarity override of 0.0 to prevent filtering c1
    with override_settings(retrieval_min_similarity=0.0):
        res = retrieval.search("Detroit factory layout", top_k=2)
        assert len(res) == 2
        assert res[0].metadata.chunk_id == "c2"


def test_bm25_only_exact_match(tmp_path: Path) -> None:
    chunks = [
        _chunk("c1", "The security clearance code is AE-0002 for employees."),
        _chunk("c2", "The kitchen guidelines for coffee machine operations."),
    ]
    retrieval, _bm25 = _seed_store_and_bm25(
        tmp_path,
        chunks,
        embeddings=[[0.0, 0.0, 1.0], [0.0, 0.0, 1.0]],
        username="bm25_only",
    )

    res = retrieval.search("AE-0002", top_k=1)
    assert len(res) == 1
    assert res[0].metadata.chunk_id == "c1"


def test_hybrid_rrf_ranking_and_deduplication(tmp_path: Path) -> None:

    chunks = [
        _chunk("c1", "Education reimbursement limit is $5000."),
        _chunk("c2", "Tuition fees details."),
        _chunk("c3", "The $5000 limit applies to academic years."),
    ]
    retrieval, _bm25 = _seed_store_and_bm25(
        tmp_path,
        chunks,
        embeddings=[
            [0.9, 0.0, 0.0],  # high semantic match
            [0.7, 0.0, 0.0],  # medium semantic match
            [0.1, 0.0, 0.0],  # low semantic match
        ],
        username="hybrid_rrf",
    )


    res = retrieval.search("reimbursement tuition $5000", top_k=3)

    # Verify deduplication and unique chunk IDs
    assert len(res) <= 3
    retrieved_ids = [c.metadata.chunk_id for c in res]
    assert len(set(retrieved_ids)) == len(retrieved_ids)

    # Verify c1 (which appears in both) has higher RRF score and is ranked first
    assert retrieved_ids[0] == "c1"


def test_fail_safe_no_bm25_hits(tmp_path: Path) -> None:
    # Query with no keyword match in corpus but strong semantic matches
    chunks = [
        _chunk("c1", "Annual leave policy."),
    ]
    retrieval, _bm25 = _seed_store_and_bm25(
        tmp_path, chunks, embeddings=[[0.9, 0.0, 0.0]], username="no_bm25"
    )

    # Semantic match returns results, BM25 has score 0
    res = retrieval.search("Annual vacation rules", top_k=1)
    assert len(res) == 1
    assert res[0].metadata.chunk_id == "c1"


def test_fail_safe_no_semantic_hits(tmp_path: Path) -> None:
    chunks = [
        _chunk("c1", "Laptop asset code ABC-7788."),
    ]
    retrieval, _bm25 = _seed_store_and_bm25(
        tmp_path, chunks, embeddings=[[0.1, 0.0, 0.0]], username="no_semantic"
    )

    res = retrieval.search("ABC-7788", top_k=1)
    assert len(res) == 1
    assert res[0].metadata.chunk_id == "c1"
