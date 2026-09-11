from __future__ import annotations

import logging
from typing import Any

from app.config import settings
from app.embeddings.embedding_engine import EmbeddingEngine, EmbeddingService
from app.models.schemas import (
    TOP_K_MAX,
    ChunkMetadata,
    ChunkType,
    DocumentChunk,
    InvalidTopKError,
)
from app.retrieval.bm25_index_manager import BM25IndexManager
from app.retrieval.query_preprocessor import QueryPreprocessor
from app.utils.language_detector import detect_language
from app.utils.localization import get_message
from app.vectorstore.chroma_manager import ChromaVectorStore

LOGGER = logging.getLogger(__name__)


class RetrievalEngineError(RuntimeError):
    """Raised when question embedding or similarity search fails."""


# Backwards-compatibility alias for the base exception
RetrievalServiceError = RetrievalEngineError


class EmptyQuestionError(RetrievalEngineError):
    """Raised when retrieval is requested for an empty question."""


class QuestionEmbeddingError(RetrievalEngineError):
    """Raised when question embedding generation fails."""


class ChromaQueryError(RetrievalEngineError):
    """Raised when ChromaDB similarity search fails."""


class InsufficientInformationError(RetrievalEngineError):
    """Raised when no retrieved chunks meet the relevance threshold."""


class RetrievalEngine:
    """Hybrid retrieval engine combining vector similarity and BM25 search."""

    def __init__(
        self,
        embedding_service: EmbeddingEngine | EmbeddingService | None = None,
        vector_store: ChromaVectorStore | None = None,
        top_k: int | None = None,
        enable_hybrid_search: bool | None = None,
        bm25_index_manager: BM25IndexManager | None = None,
    ) -> None:
        """Initialize the retrieval engine with optional injected dependencies."""
        # Initialize vector store FIRST to check dimension compatibility before loading model
        self._store = vector_store or ChromaVectorStore()

        # Now initialize embedding engine (which may load a potentially large model)
        self._service = embedding_service or EmbeddingEngine(
            batch_size=settings.embedding_batch_size,
        )

        self._default_top_k = top_k if top_k is not None else settings.retrieval_top_k
        self._min_similarity = settings.retrieval_min_similarity

        self._enable_hybrid_search = (
            enable_hybrid_search
            if enable_hybrid_search is not None
            else settings.enable_hybrid_search
        )
        self._bm25_index_manager = bm25_index_manager

    def embed_question(self, question: str) -> list[float]:
        """Generate an embedding vector for a user question."""
        cleaned = question.strip()
        if not cleaned:
            LOGGER.error("Question validation failed: empty question.")
            raise EmptyQuestionError("Question must not be empty or whitespace-only.")

        LOGGER.info("Question received: question=%.80s", cleaned)
        print(f"[3] QUERY EMBEDDING\n    Sending question to embedding model...\n    Model: {settings.embedding_model_name}")

        try:
            embeddings = self._service.embed_texts([cleaned])
        except Exception as exc:
            print(f"    Question embedding failed\n    Error: {exc}")
            LOGGER.exception("Question embedding generation failed.")
            raise QuestionEmbeddingError(
                "Failed to generate embedding for the question."
            ) from exc

        embedding = embeddings[0]
        print(f"    Embedding generated successfully\n    Vector dimensions: {len(embedding)}")
        LOGGER.info(
            "Question embedding generated: dimension=%s",
            len(embedding),
        )
        return embedding

    def search(
        self,
        question: str,
        top_k: int | None = None,
    ) -> list[DocumentChunk]:
        """Embed a question and search ChromaDB/BM25 for the most relevant chunks."""
        effective_top_k = top_k if top_k is not None else self._default_top_k
        self._validate_top_k(effective_top_k)

        # 1. Query preprocessing
        raw_question = question
        normalized_query = QueryPreprocessor.preprocess(question)

        LOGGER.info(
            "Retrieval request accepted: normalized_query=%.80s top_k=%s",
            normalized_query,
            effective_top_k,
        )

        # Log DEBUG-only retrieval diagnostics
        if LOGGER.isEnabledFor(logging.DEBUG):
            try:
                lang = detect_language(normalized_query)
            except Exception:
                lang = "unknown"
            LOGGER.debug("DEBUG RAG DIAGNOSTICS: Original raw query: %r", raw_question)
            LOGGER.debug(
                "DEBUG RAG DIAGNOSTICS: Normalized query: %r", normalized_query
            )
            LOGGER.debug("DEBUG RAG DIAGNOSTICS: Detected query language: %s", lang)

        # Handle empty query after preprocessing
        if not normalized_query:
            LOGGER.error("Normalized question is empty.")
            raise EmptyQuestionError("Question must not be empty after preprocessing.")

        # Embedding generation
        question_embedding = self.embed_question(normalized_query)

        total_collection_count = self._store.collection.count()
        if total_collection_count == 0:
            LOGGER.info("Collection is empty: collection=%s", self._store.collection_name)
            return []

        LOGGER.info(
            "Retrieval started: top_k=%s collection=%s total_chunks=%s",
            effective_top_k,
            self._store.collection_name,
            total_collection_count,
        )

        # Check if hybrid search is enabled and index manager is provided
        if self._enable_hybrid_search and self._bm25_index_manager is not None:
            LOGGER.info(
                "Hybrid search execution started: semantic_top_k=%s bm25_top_k=%s",
                settings.semantic_top_k,
                settings.bm25_top_k,
            )

            # 1. Semantic candidates
            try:
                n_results_semantic = min(settings.semantic_top_k, total_collection_count)
                raw_semantic = self._store.collection.query(
                    query_embeddings=[question_embedding],
                    n_results=n_results_semantic,
                    include=["documents", "metadatas", "distances"],
                )
            except Exception as exc:
                LOGGER.exception(
                    "ChromaDB similarity search failed during hybrid search."
                )
                raise ChromaQueryError("ChromaDB similarity search failed.") from exc

            semantic_candidates = self._parse_query_results(raw_semantic)
            semantic_distances = raw_semantic.get("distances", [[]])[0]

            print(f"[4] VECTOR RETRIEVAL\n    Searching ChromaDB...\n    Collection: {self._store.collection_name}\n    Vectors/chunks retrieved: {len(semantic_candidates)}")

            filtered_semantic = []
            semantic_diagnostics = []
            if semantic_distances:
                for chunk, dist in zip(semantic_candidates, semantic_distances):
                    similarity = 1.0 - dist
                    semantic_diagnostics.append((chunk.metadata.chunk_id, similarity))
                    if similarity >= self._min_similarity:
                        filtered_semantic.append(chunk)
                if not filtered_semantic:
                    filtered_semantic = semantic_candidates
            else:
                filtered_semantic = semantic_candidates
                semantic_diagnostics = [
                    (c.metadata.chunk_id, 1.0) for c in semantic_candidates
                ]

            # 2. BM25 candidates
            bm25_candidates = self._bm25_index_manager.search(
                normalized_query, settings.bm25_top_k
            )
            print(f"[5] BM25 RETRIEVAL\n    Searching BM25...\n    BM25 results: {len(bm25_candidates)}")

            # 3. Reciprocal Rank Fusion (RRF)
            results = self._reciprocal_rank_fusion(
                filtered_semantic,
                bm25_candidates,
                rrf_k=settings.rrf_k,
            )
            results = results[:effective_top_k]

            print(f"[6] HYBRID RETRIEVAL\n    Vector results: {len(filtered_semantic)}\n    BM25 results: {len(bm25_candidates)}\n    RRF candidates: {len(results)}")

        else:
            # Semantic search only
            LOGGER.info(
                "Semantic-only search execution started: top_k=%s",
                effective_top_k,
            )
            try:
                n_results_semantic = min(effective_top_k, total_collection_count)
                raw_results = self._store.collection.query(
                    query_embeddings=[question_embedding],
                    n_results=n_results_semantic,
                    include=["documents", "metadatas", "distances"],
                )
            except Exception as exc:
                LOGGER.exception("ChromaDB similarity search failed.")
                raise ChromaQueryError("ChromaDB similarity search failed.") from exc

            results = self._parse_query_results(raw_results)
            if results:
                distances_list = raw_results.get("distances", [[]])[0]
                if distances_list:
                    filtered_results = []
                    for chunk, dist in zip(results, distances_list):
                        similarity = 1.0 - dist
                        if similarity >= self._min_similarity:
                            filtered_results.append(chunk)
                    if filtered_results:
                        results = filtered_results

            print(f"[4] VECTOR RETRIEVAL\n    Searching ChromaDB...\n    Collection: {self._store.collection_name}\n    Vectors/chunks retrieved: {len(results)}")
            print("[5] BM25 RETRIEVAL\n    BM25 retrieval: SKIPPED")
            print("[6] HYBRID RETRIEVAL\n    Hybrid RRF retrieval: SKIPPED")

            if LOGGER.isEnabledFor(logging.DEBUG):
                LOGGER.debug(
                    "DEBUG RAG DIAGNOSTICS: Semantic-only candidates: %r",
                    [c.metadata.chunk_id for c in results],
                )

        # Final diagnostics logs
        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug(
                "DEBUG RAG DIAGNOSTICS: Final top-K selected chunk IDs: %r",
                [c.metadata.chunk_id for c in results],
            )

        if not results:
            if self._store.collection.count() > 0:
                LOGGER.warning(
                    "No chunks satisfy relevance threshold or keyword matching: collection=%s",
                    self._store.collection_name,
                )
                raise InsufficientInformationError(get_message("empty_context", "en"))
            else:
                LOGGER.info(
                    "Empty vector database or no matching chunks: collection=%s top_k=%s",
                    self._store.collection_name,
                    effective_top_k,
                )
                return []

        LOGGER.info(
            "Number of chunks retrieved: retrieved=%s top_k=%s",
            len(results),
            effective_top_k,
        )

        LOGGER.info(
            "Retrieval completed: retrieved=%s top_k=%s",
            len(results),
            effective_top_k,
        )
        return results

    @staticmethod
    def _reciprocal_rank_fusion(
        semantic_results: list[DocumentChunk],
        bm25_results: list[DocumentChunk],
        rrf_k: int = 60,
    ) -> list[DocumentChunk]:
        """Merge and rank documents using Reciprocal Rank Fusion (RRF)."""
        chunk_map: dict[str, DocumentChunk] = {}

        semantic_ranks: dict[str, int] = {}
        for rank, chunk in enumerate(semantic_results, start=1):
            cid = chunk.metadata.chunk_id
            chunk_map[cid] = chunk
            semantic_ranks[cid] = rank

        bm25_ranks: dict[str, int] = {}
        for rank, chunk in enumerate(bm25_results, start=1):
            cid = chunk.metadata.chunk_id
            chunk_map[cid] = chunk
            bm25_ranks[cid] = rank

        rrf_scores: dict[str, float] = {}
        for cid in chunk_map:
            score = 0.0
            if cid in semantic_ranks:
                score += 1.0 / (rrf_k + semantic_ranks[cid])
            if cid in bm25_ranks:
                score += 1.0 / (rrf_k + bm25_ranks[cid])
            rrf_scores[cid] = score

        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug(
                "DEBUG RAG DIAGNOSTICS: RRF intermediate scores: %r", rrf_scores
            )

        sorted_cids = sorted(
            rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True
        )
        return [chunk_map[cid] for cid in sorted_cids]

    @staticmethod
    def _validate_top_k(top_k: int) -> None:
        """Reject non-positive integers and excessive top_k values."""
        if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k <= 0:
            LOGGER.error("Invalid top_k value: top_k=%r", top_k)
            raise InvalidTopKError(f"top_k must be a positive integer, got {top_k!r}.")
        if top_k > TOP_K_MAX:
            LOGGER.error(
                "Unreasonable top_k value rejected: top_k=%s max=%s",
                top_k,
                TOP_K_MAX,
            )
            raise InvalidTopKError(
                f"top_k={top_k} exceeds the maximum allowed value of {TOP_K_MAX}."
            )

    @staticmethod
    def _parse_query_results(raw: dict[str, Any]) -> list[DocumentChunk]:
        """Convert raw ChromaDB query output into ordered ``DocumentChunk`` objects."""
        ids_list = raw.get("ids", [[]])[0]
        docs_list = raw.get("documents", [[]])[0]
        meta_list = raw.get("metadatas", [[]])[0]

        if not ids_list:
            return []

        results: list[DocumentChunk] = []
        for doc, meta in zip(docs_list, meta_list):
            raw_ctype = meta.get("chunk_type", "text")
            try:
                chunk_type_val = ChunkType(raw_ctype)
            except Exception:
                chunk_type_val = ChunkType.TEXT

            chunk_meta = ChunkMetadata(
                source_file=str(meta.get("source_file", "")),
                page_number=int(meta.get("page_number", 1)),
                chunk_id=str(meta.get("chunk_id", "")),
                document_type=str(meta.get("document_type", "")),
                chunk_type=chunk_type_val,
                document_name=str(meta.get("document_name", "")),
                username=str(meta.get("username", "")),
                image_path=meta.get("image_path"),
                image_hash=meta.get("image_hash"),
                table_markdown=meta.get("table_markdown"),
                table_json=meta.get("table_json"),
                ocr_engine=meta.get("ocr_engine"),
                ocr_confidence=(
                    float(meta["ocr_confidence"])
                    if meta.get("ocr_confidence") is not None
                    else None
                ),
                ocr_processing_time_ms=(
                    float(meta["ocr_processing_time_ms"])
                    if meta.get("ocr_processing_time_ms") is not None
                    else None
                ),
            )
            results.append(
                DocumentChunk(
                    content=doc,
                    metadata=chunk_meta,
                )
            )

        return results


# ---------------------------------------------------------------------------
# Backwards-compatibility alias — RetrievalService maps to RetrievalEngine.
# ---------------------------------------------------------------------------
RetrievalService = RetrievalEngine
