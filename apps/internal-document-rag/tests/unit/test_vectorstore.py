"""Unit tests for the ChromaDB vector store wrapper."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.models.schemas import ChunkMetadata, DocumentChunk
from app.vectorstore.chroma_manager import ChromaVectorStore, VectorStoreError


@pytest.fixture
def dummy_chunks() -> list[DocumentChunk]:
    return [
        DocumentChunk(
            content="Chroma vector store content 1",
            metadata=ChunkMetadata(
                source_file="guide.pdf",
                page_number=1,
                chunk_id="guide.pdf-p1-c1",
                document_type="pdf",
            ),
        )
    ]


def test_vectorstore_adds_chunks(
    tmp_path: Path, dummy_chunks: list[DocumentChunk]
) -> None:
    """ChromaVectorStore should upsert document chunks and embeddings into collection."""
    with patch("chromadb.PersistentClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.metadata = {"embedding_dimension": 384}
        mock_collection.get.return_value = {
            "ids": ["guide.pdf-p1-c1"],
            "embeddings": [],
        }
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client.get_collection.return_value = mock_collection
        mock_client_cls.return_value = mock_client

        store = ChromaVectorStore(
            persist_directory=tmp_path, collection_name="test_col"
        )
        ids = store.add_chunks(dummy_chunks, [[0.1] * 384])

        assert ids == ["guide.pdf-p1-c1"]
        mock_collection.upsert.assert_called_once()


def test_vectorstore_deletes_document_chunks(tmp_path: Path) -> None:
    """delete_document should invoke collection.delete with source_file metadata filter."""
    with patch("chromadb.PersistentClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.metadata = {"embedding_dimension": 384}
        mock_collection.get.return_value = {"ids": [], "embeddings": []}
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client.get_collection.return_value = mock_collection
        mock_client_cls.return_value = mock_client

        store = ChromaVectorStore(
            persist_directory=tmp_path, collection_name="test_col"
        )
        store.delete_document("guide.pdf")

        mock_collection.delete.assert_called_once_with(
            where={"source_file": "guide.pdf"}
        )


def test_vectorstore_rejects_empty_chunks(tmp_path: Path) -> None:
    """Inserting empty chunk lists must raise VectorStoreError."""
    with patch("chromadb.PersistentClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.metadata = {"embedding_dimension": 384}
        mock_collection.get.return_value = {"ids": [], "embeddings": []}
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client.get_collection.return_value = mock_collection
        mock_client_cls.return_value = mock_client

        store = ChromaVectorStore(persist_directory=tmp_path)
        with pytest.raises(VectorStoreError, match="Cannot insert an empty chunk list"):
            store.add_chunks([], [])


def test_vectorstore_rejects_embedding_count_mismatch(
    tmp_path: Path, dummy_chunks: list[DocumentChunk]
) -> None:
    """Embedding count mismatch against chunk count must raise VectorStoreError."""
    with patch("chromadb.PersistentClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.metadata = {"embedding_dimension": 384}
        mock_collection.get.return_value = {"ids": [], "embeddings": []}
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client.get_collection.return_value = mock_collection
        mock_client_cls.return_value = mock_client

        store = ChromaVectorStore(persist_directory=tmp_path)
        with pytest.raises(
            VectorStoreError, match="Embedding count must match chunk count"
        ):
            store.add_chunks(dummy_chunks, [[0.1] * 384, [0.2] * 384])
