"""End-to-end embedding and vector storage pipeline for Step 5."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path

from app.config import settings
from app.embeddings.embedding_engine import (
    EmbeddingEngine,
    EmbeddingEngineError,
    EmbeddingService,
    EmbeddingServiceError,
)
from app.models.schemas import DocumentChunk
from app.vectorstore.chroma_manager import ChromaVectorStore, VectorStoreError

LOGGER = logging.getLogger(__name__)


class EmbeddingPipelineError(RuntimeError):
    """Raised when the embedding pipeline fails at any stage."""


class EmbeddingPipeline:

    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        vector_store: ChromaVectorStore | None = None,
        persist_directory: Path | str | None = None,
        collection_name: str | None = None,
    ) -> None:
        """Initialize the pipeline with optional injected dependencies.

        Args:
            embedding_service: Pre-constructed ``EmbeddingService`` instance.
                When ``None``, a default service is created using
                ``settings.embedding_model_name`` and
                ``settings.embedding_batch_size``.
            vector_store: Pre-constructed ``ChromaVectorStore`` instance.
                When ``None``, a default store is created using
                ``settings.chroma_db_dir`` and ``collection_name``.
            persist_directory: ChromaDB persistence path override.  Only used
                when ``vector_store`` is ``None``.
            collection_name: ChromaDB collection name.  Only used when
                ``vector_store`` is ``None``.
        """
        try:
            self._service = embedding_service or EmbeddingService(
                batch_size=settings.embedding_batch_size,
            )
        except EmbeddingServiceError as exc:
            LOGGER.error(
                "Embedding pipeline initialization failed while loading model: %s", exc
            )
            raise EmbeddingPipelineError(
                "Embedding pipeline initialization failed while loading the model."
            ) from exc

        try:
            self._store = vector_store or ChromaVectorStore(
                persist_directory=persist_directory,
                collection_name=collection_name,
            )
        except VectorStoreError as exc:
            LOGGER.error(
                "Embedding pipeline initialization failed for ChromaDB: %s", exc
            )
            raise EmbeddingPipelineError(
                "Embedding pipeline initialization failed for ChromaDB."
            ) from exc

    def run(self, chunks: Sequence[DocumentChunk]) -> list[str]:
        """Generate embeddings for ``chunks`` and persist them into ChromaDB.

        Args:
            chunks: Non-empty sequence of ``DocumentChunk`` objects produced by
                Step 4 chunking.

        Returns:
            List of ChromaDB document IDs (one per chunk) that were upserted.

        Raises:
            EmbeddingPipelineError: If the chunk list is empty, embedding
                generation fails, or ChromaDB persistence fails.
        """
        if not chunks:
            raise EmbeddingPipelineError("Pipeline received an empty chunk list.")

        LOGGER.info(
            "Embedding pipeline started for %s chunks.",
            len(chunks),
        )

        try:
            embeddings = self._service.generate_embeddings(list(chunks))
        except EmbeddingServiceError as exc:
            LOGGER.error(
                "Embedding pipeline failed during embedding generation: %s", exc
            )
            raise EmbeddingPipelineError(
                "Embedding pipeline failed during embedding generation."
            ) from exc

        LOGGER.info(
            "Embedding pipeline: %s embeddings generated (dim=%s).",
            len(embeddings),
            len(embeddings[0]) if embeddings else 0,
        )

        try:
            inserted_ids = self._store.add_chunks(list(chunks), embeddings)
        except VectorStoreError as exc:
            LOGGER.error(
                "Embedding pipeline failed during vector store insertion: %s", exc
            )
            raise EmbeddingPipelineError(
                "Embedding pipeline failed during vector store insertion."
            ) from exc

        LOGGER.info(
            "Embedding pipeline completed: %s chunks persisted to collection=%s.",
            len(inserted_ids),
            self._store.collection_name,
        )
        return inserted_ids
