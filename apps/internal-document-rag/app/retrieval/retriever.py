"""High-level retrieval orchestrator for Step 6 semantic search."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.config import settings
from app.embeddings.embedding_engine import (
    EmbeddingEngine,
    EmbeddingEngine as EmbeddingService,
    EmbeddingServiceError,
)
from app.models.schemas import DocumentChunk, InvalidTopKError
from app.retrieval.retrieval_engine import (
    InsufficientInformationError,
    RetrievalEngine,
    RetrievalEngine as RetrievalService,
    RetrievalServiceError,
)
from app.vectorstore.chroma_manager import ChromaVectorStore, VectorStoreError

LOGGER = logging.getLogger(__name__)


class RetrieverError(RuntimeError):
    """Raised when the retrieval pipeline fails at any stage."""


class DocumentRetriever:

    def __init__(
        self,
        retrieval_service: RetrievalEngine | None = None,
        embedding_service: EmbeddingEngine | None = None,
        vector_store: ChromaVectorStore | None = None,
        persist_directory: Path | str | None = None,
        collection_name: str | None = None,
        top_k: int | None = None,
        bm25_index_manager: Any = None,
    ) -> None:
        """Initialize the retriever with optional injected dependencies."""
        if retrieval_service is not None:
            self._service = retrieval_service
            return

        try:
            svc = embedding_service or EmbeddingEngine(
                batch_size=settings.embedding_batch_size,
            )
        except EmbeddingServiceError as exc:
            LOGGER.error("Retriever init failed while loading embedding model: %s", exc)
            raise RetrieverError(
                "Retriever initialization failed while loading the embedding model."
            ) from exc

        try:
            store = vector_store or ChromaVectorStore(
                persist_directory=persist_directory,
                collection_name=collection_name,
            )
        except VectorStoreError as exc:
            LOGGER.error("Retriever init failed for ChromaDB: %s", exc)
            raise RetrieverError(
                "Retriever initialization failed for ChromaDB."
            ) from exc

        self._service = RetrievalEngine(
            embedding_service=svc,
            vector_store=store,
            top_k=top_k,
            bm25_index_manager=bm25_index_manager,
        )

    def retrieve(
        self,
        question: str,
        top_k: int | None = None,
    ) -> list[DocumentChunk]:
        """Retrieve the most relevant document chunks for a user question.

        Args:
            question: User question string.
            top_k: Number of results to return.  Uses the service default
                when ``None``.

        Returns:
            List of ``DocumentChunk`` objects sorted by relevance.

        Raises:
            RetrieverError: If the question is invalid, embedding fails,
                or the similarity search fails.
        """
        LOGGER.info("Retriever received question: %.80s...", question.strip())

        try:
            results = self._service.search(question, top_k=top_k)
        except InsufficientInformationError:
            raise
        except (RetrievalServiceError, InvalidTopKError) as exc:
            LOGGER.error("Retriever failed: %s", exc)
            raise RetrieverError("Retrieval pipeline failed.") from exc

        LOGGER.info(
            "Retriever completed: %s chunks retrieved.",
            len(results),
        )
        return results
