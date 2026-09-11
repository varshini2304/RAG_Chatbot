"""ChromaDB persistence layer for embedded document chunks."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import chromadb
from chromadb.errors import NotFoundError

from app.config import settings
from app.models.schemas import DocumentChunk
from app.vectorstore.collection_guard import assert_collection_dimension_matches

LOGGER = logging.getLogger(__name__)

REQUIRED_METADATA_FIELDS = ("source_file", "page_number", "chunk_id", "document_type")


class VectorStoreError(RuntimeError):
    """Raised when ChromaDB initialization, validation, or insertion fails."""


class ChromaVectorStore:
    """Manage local ChromaDB collection creation and document insertion."""

    def __init__(
        self,
        persist_directory: Path | str | None = None,
        collection_name: str | None = None,
    ) -> None:
        """Initialize a persistent local ChromaDB collection."""
        self.persist_directory = Path(persist_directory or settings.chroma_db_dir)
        self.collection_name = collection_name or settings.chroma_collection_name

        try:
            self.persist_directory.mkdir(parents=True, exist_ok=True)
            LOGGER.info("Initializing ChromaDB at %s", self.persist_directory)
            from chromadb.config import Settings as ChromaSettings

            self.client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self.collection = self._get_or_create_collection(self.collection_name)
            assert_collection_dimension_matches(
                self.collection, settings.embedding_dimension
            )
        except Exception as exc:
            LOGGER.exception(
                "ChromaDB initialization failed at %s", self.persist_directory
            )
            from app.vectorstore.collection_guard import EmbeddingDimensionMismatchError

            if isinstance(exc, EmbeddingDimensionMismatchError):
                raise
            raise VectorStoreError(
                "Failed to initialize ChromaDB vector store."
            ) from exc

    def _get_or_create_collection(self, collection_name: str) -> Any:
        """Create or reuse the configured ChromaDB collection."""
        LOGGER.info("Creating or loading ChromaDB collection: %s", collection_name)
        collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={
                "description": "Internal document chunks for Step 5 embeddings",
                "hnsw:space": "cosine",
                "embedding_model_name": settings.embedding_model_name,
                "embedding_dimension": settings.embedding_dimension,
            },
        )
        LOGGER.info("ChromaDB collection ready: %s", collection_name)
        return collection

    def _refresh_collection_handle(self) -> None:
        """Recreate the collection handle after an out-of-band delete."""
        LOGGER.warning(
            "Refreshing stale ChromaDB collection handle for %s",
            self.collection_name,
        )
        self.collection = self._get_or_create_collection(self.collection_name)

    def add_chunks(
        self,
        chunks: Sequence[DocumentChunk],
        embeddings: Sequence[Sequence[float]],
    ) -> list[str]:

        self._validate_insert_payload(chunks, embeddings)

        ids = [chunk.metadata.chunk_id for chunk in chunks]
        documents = [chunk.content for chunk in chunks]
        metadatas = [self._metadata_to_chroma(chunk) for chunk in chunks]

        LOGGER.info(
            "Upserting %s chunks into ChromaDB collection=%s",
            len(chunks),
            self.collection_name,
        )

        try:
            self.collection.upsert(
                ids=ids,
                documents=documents,
                embeddings=[list(embedding) for embedding in embeddings],
                metadatas=metadatas,
            )
        except Exception as exc:
            if isinstance(exc, RuntimeError) and "upsert failed" in str(exc):
                LOGGER.exception("ChromaDB upsert failed for %s chunks", len(chunks))
                raise VectorStoreError(
                    "Failed to insert chunks into ChromaDB."
                ) from exc

            # Attempt collection handle refresh for out-of-band deleted collections
            LOGGER.warning(
                "ChromaDB upsert exception encountered (%s); attempting handle refresh",
                exc,
            )
            try:
                self._refresh_collection_handle()
                self.collection.upsert(
                    ids=ids,
                    documents=documents,
                    embeddings=[list(embedding) for embedding in embeddings],
                    metadatas=metadatas,
                )
            except Exception as retry_exc:
                LOGGER.exception(
                    "ChromaDB upsert failed for %s chunks after refresh", len(chunks)
                )
                raise VectorStoreError(
                    "Failed to insert chunks into ChromaDB."
                ) from retry_exc

        self._validate_upsert_result(ids)
        LOGGER.info(
            "Upserted %s chunks into ChromaDB collection=%s",
            len(ids),
            self.collection_name,
        )
        return ids

    def delete_document(self, source_file: str) -> None:
        """Delete all chunks associated with a source document."""
        LOGGER.info("Deleting chunks for %s from ChromaDB.", source_file)
        try:
            self.collection.delete(where={"source_file": source_file})
        except NotFoundError:
            self._refresh_collection_handle()
            try:
                self.collection.delete(where={"source_file": source_file})
            except Exception as exc:
                LOGGER.exception(
                    "Failed to delete chunks for document %s after refresh", source_file
                )
                raise VectorStoreError(
                    f"Failed to delete chunks for document '{source_file}'."
                ) from exc
        except Exception as exc:
            LOGGER.exception("Failed to delete chunks for document %s", source_file)
            raise VectorStoreError(
                f"Failed to delete chunks for document '{source_file}'."
            ) from exc
        LOGGER.info("Deleted chunks for %s from ChromaDB.", source_file)

    def clear_workspace(self) -> None:
        """Delete all chunks from the ChromaDB collection."""
        LOGGER.info(
            "Clearing all chunks from ChromaDB collection %s", self.collection_name
        )
        try:
            results = self.collection.get(include=[])
        except NotFoundError:
            self._refresh_collection_handle()
            results = self.collection.get(include=[])
        try:
            if results and results["ids"]:
                self.collection.delete(ids=results["ids"])
            LOGGER.info(
                "Cleared all chunks from ChromaDB collection %s", self.collection_name
            )
        except Exception as exc:
            LOGGER.exception(
                "Failed to clear ChromaDB collection %s", self.collection_name
            )
            raise VectorStoreError("Failed to clear ChromaDB collection.") from exc

    @staticmethod
    def _metadata_to_chroma(
        chunk: DocumentChunk,
    ) -> dict[str, str | int | float | bool]:
        """Convert typed chunk metadata into ChromaDB-compatible metadata."""
        if hasattr(chunk.metadata, "to_chroma_dict"):
            return chunk.metadata.to_chroma_dict()
        data = chunk.metadata.model_dump(mode="json", exclude_none=True)
        return {k: v for k, v in data.items() if isinstance(v, (str, int, float, bool))}

    def _validate_upsert_result(self, ids: list[str]) -> None:
        """Verify that all upserted IDs are present in the collection."""
        try:
            result = self.collection.get(ids=ids, include=[])
        except NotFoundError:
            self._refresh_collection_handle()
            result = self.collection.get(ids=ids, include=[])
        stored_ids = result.get("ids", [])
        if len(stored_ids) != len(ids):
            LOGGER.error(
                "ChromaDB upsert validation failed: stored_count=%s expected=%s",
                len(stored_ids),
                len(ids),
            )
            raise VectorStoreError("ChromaDB upsert count validation failed.")

    @classmethod
    def _validate_insert_payload(
        cls,
        chunks: Sequence[DocumentChunk],
        embeddings: Sequence[Sequence[float]],
    ) -> None:
        """Validate chunk, embedding, and metadata counts before upsert."""
        if not chunks:
            raise VectorStoreError("Cannot insert an empty chunk list into ChromaDB.")

        if len(embeddings) != len(chunks):
            LOGGER.error(
                "Vector store validation failed: embedding_count=%s chunk_count=%s",
                len(embeddings),
                len(chunks),
            )
            raise VectorStoreError("Embedding count must match chunk count.")

        metadata_count = 0
        for chunk in chunks:
            metadata = cls._metadata_to_chroma(chunk)
            missing_fields = [
                field
                for field in REQUIRED_METADATA_FIELDS
                if field not in metadata or metadata[field] in ("", None)
            ]
            if missing_fields:
                LOGGER.error(
                    "Vector store validation failed for chunk_id=%s missing_metadata=%s",
                    chunk.metadata.chunk_id,
                    missing_fields,
                )
                raise VectorStoreError("Chunk metadata is missing required fields.")
            metadata_count += 1

        if metadata_count != len(chunks):
            LOGGER.error(
                "Vector store validation failed: metadata_count=%s chunk_count=%s",
                metadata_count,
                len(chunks),
            )
            raise VectorStoreError("Metadata count must match chunk count.")

        expected_dimension = len(embeddings[0])
        if expected_dimension <= 0:
            raise VectorStoreError("Embedding vectors must not be empty.")
        for embedding in embeddings:
            if len(embedding) != expected_dimension:
                LOGGER.error(
                    "Vector store validation failed: inconsistent embedding dimensions."
                )
                raise VectorStoreError("All embeddings must have the same dimension.")
