
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.config import settings as app_settings
from app.models.schemas import (
    ChunkMetadata,
    DocumentChunk,
    ExtractedPage,
    ExtractedPdfDocument,
)
from app.services.workspace_service import WorkspaceService
from app.vectorstore.chroma_manager import ChromaVectorStore


@contextmanager
def override_settings(**kwargs):
    originals = {k: getattr(app_settings, k) for k in kwargs}
    try:
        for k, v in kwargs.items():
            object.__setattr__(app_settings, k, v)
        yield
    finally:
        for k, v in originals.items():
            object.__setattr__(app_settings, k, v)


def test_delete_document_removes_file_disk_and_vectorstore(
    tmp_path: Path,
) -> None:
    with override_settings(upload_dir=tmp_path):
        user_dir = WorkspaceService.get_upload_directory("admin")
        doc_file = user_dir / "test_doc.pdf"
        doc_file.write_text("dummy PDF content")
        WorkspaceService.save_hashes("admin", {"some_hash": "test_doc.pdf"})

        with patch("app.services.workspace_service.ChromaVectorStore") as mock_store_cls:
            mock_vectorstore = MagicMock()
            mock_store_cls.return_value = mock_vectorstore

            WorkspaceService.delete_document("admin", "test_doc.pdf")

        # Verify physical file deletion
        assert not doc_file.exists()

        # Verify ChromaVectorStore delete call
        mock_vectorstore.delete_document.assert_called_once_with("test_doc.pdf")

        # Verify hash registry cleanup
        assert WorkspaceService.load_hashes("admin") == {}


def test_clear_workspace_removes_all_files_and_clears_vectors(
    tmp_path: Path,
) -> None:
    with override_settings(upload_dir=tmp_path):
        user_dir = WorkspaceService.get_upload_directory("admin")
        doc_file_1 = user_dir / "doc1.pdf"
        doc_file_2 = user_dir / "doc2.txt"
        doc_file_1.write_text("PDF content")
        doc_file_2.write_text("TXT content")
        WorkspaceService.save_hashes(
            "admin", {"hash1": "doc1.pdf", "hash2": "doc2.txt"}
        )

        with patch("app.services.workspace_service.ChromaVectorStore") as mock_store_cls:
            mock_vectorstore = MagicMock()
            mock_store_cls.return_value = mock_vectorstore

            WorkspaceService.clear_workspace("admin")

        # Verify all physical files unlinked
        assert not doc_file_1.exists()
        assert not doc_file_2.exists()

        # Verify ChromaVectorStore clear call
        mock_vectorstore.clear_workspace.assert_called_once()

        # Verify hash registry reset
        assert WorkspaceService.load_hashes("admin") == {}



def test_reupload_same_filename_overwrites_chunks_real(tmp_path: Path) -> None:
    """If a filename already exists, prepare_document_upload should delete old chunks/files/hashes."""
    username = "test_user_reupload_real"
    user_dir = tmp_path / "uploads"
    user_dir.mkdir(parents=True, exist_ok=True)
    chroma_dir = tmp_path / "chroma"
    chroma_dir.mkdir(parents=True, exist_ok=True)

    with override_settings(
        data_dir=tmp_path,
        upload_dir=user_dir,
        chroma_db_dir=chroma_dir,
        allowed_upload_extensions=("pdf", "txt"),
        embedding_dimension=3,
    ):
        collection_name = WorkspaceService.get_collection_name(username)
        store = ChromaVectorStore(
            persist_directory=chroma_dir, collection_name=collection_name
        )

        file_path = WorkspaceService.get_upload_directory(username) / "policy.pdf"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("V1 Content")

        chunks_v1 = [
            DocumentChunk(
                content="Chunk 1 content",
                metadata=ChunkMetadata(
                    source_file="policy.pdf",
                    page_number=1,
                    chunk_id="policy.pdf-p1-c1",
                    document_type="pdf",
                ),
            ),
            DocumentChunk(
                content="Chunk 2 content",
                metadata=ChunkMetadata(
                    source_file="policy.pdf",
                    page_number=2,
                    chunk_id="policy.pdf-p2-c1",
                    document_type="pdf",
                ),
            ),
            DocumentChunk(
                content="Chunk 3 content",
                metadata=ChunkMetadata(
                    source_file="policy.pdf",
                    page_number=3,
                    chunk_id="policy.pdf-p3-c1",
                    document_type="pdf",
                ),
            ),
        ]

        store.add_chunks(chunks_v1, [[0.1, 0.2, 0.3], [0.1, 0.2, 0.3], [0.1, 0.2, 0.3]])
        WorkspaceService.update_hash(username, "hash1", "policy.pdf")

        stored_v1 = store.collection.get(where={"source_file": "policy.pdf"})
        assert len(stored_v1["ids"]) == 3

        WorkspaceService.prepare_document_upload(username, "policy.pdf")

        assert not file_path.exists()
        assert store.collection.get(where={"source_file": "policy.pdf"})["ids"] == []
        assert WorkspaceService.load_hashes(username) == {}

        file_path.write_text("V2 Content")
        chunks_v2 = [
            DocumentChunk(
                content="Chunk 1 content V2",
                metadata=ChunkMetadata(
                    source_file="policy.pdf",
                    page_number=1,
                    chunk_id="policy.pdf-p1-c1",
                    document_type="pdf",
                ),
            )
        ]
        store.add_chunks(chunks_v2, [[0.1, 0.2, 0.3]])
        WorkspaceService.update_hash(username, "hash2", "policy.pdf")

        stored_v2 = store.collection.get(where={"source_file": "policy.pdf"})
        assert len(stored_v2["ids"]) == 1
        assert stored_v2["ids"] == ["policy.pdf-p1-c1"]


def test_multiple_overwrite_cycles(tmp_path: Path) -> None:

    username = "test_user_overwrite_cycles"
    user_dir = tmp_path / "uploads"
    user_dir.mkdir(parents=True, exist_ok=True)
    chroma_dir = tmp_path / "chroma"
    chroma_dir.mkdir(parents=True, exist_ok=True)

    with override_settings(
        data_dir=tmp_path,
        upload_dir=user_dir,
        chroma_db_dir=chroma_dir,
        allowed_upload_extensions=("pdf", "txt"),
        embedding_dimension=3,
    ):
        collection_name = WorkspaceService.get_collection_name(username)
        store = ChromaVectorStore(
            persist_directory=chroma_dir, collection_name=collection_name
        )

        file_path = WorkspaceService.get_upload_directory(username) / "policy.pdf"
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Cycle 1: Upload policy.pdf (Version 1)
        file_path.write_text("V1 Content")
        chunks_v1 = [
            DocumentChunk(
                content="Chunk 1 content V1",
                metadata=ChunkMetadata(
                    source_file="policy.pdf",
                    page_number=1,
                    chunk_id="policy.pdf-p1-c1",
                    document_type="pdf",
                ),
            )
        ]
        store.add_chunks(chunks_v1, [[0.1, 0.2, 0.3]])
        WorkspaceService.update_hash(username, "hash1", "policy.pdf")

        # Cycle 2: Upload a different policy.pdf (Version 2)
        WorkspaceService.prepare_document_upload(username, "policy.pdf")
        assert not file_path.exists()
        assert store.collection.get(where={"source_file": "policy.pdf"})["ids"] == []
        assert WorkspaceService.load_hashes(username) == {}

        file_path.write_text("V2 Content")
        chunks_v2 = [
            DocumentChunk(
                content="Chunk 1 content V2",
                metadata=ChunkMetadata(
                    source_file="policy.pdf",
                    page_number=1,
                    chunk_id="policy.pdf-p1-c1",
                    document_type="pdf",
                ),
            ),
            DocumentChunk(
                content="Chunk 2 content V2",
                metadata=ChunkMetadata(
                    source_file="policy.pdf",
                    page_number=2,
                    chunk_id="policy.pdf-p2-c1",
                    document_type="pdf",
                ),
            ),
        ]
        store.add_chunks(chunks_v2, [[0.1, 0.2, 0.3], [0.1, 0.2, 0.3]])
        WorkspaceService.update_hash(username, "hash2", "policy.pdf")

        # Cycle 3: Delete it
        WorkspaceService.delete_document(username, "policy.pdf")
        assert not file_path.exists()
        assert store.collection.get(where={"source_file": "policy.pdf"})["ids"] == []
        assert WorkspaceService.load_hashes(username) == {}

        # Cycle 4: Upload policy.pdf again (Version 3)
        WorkspaceService.prepare_document_upload(username, "policy.pdf")
        file_path.write_text("V3 Content")
        chunks_v3 = [
            DocumentChunk(
                content="Chunk 1 content V3",
                metadata=ChunkMetadata(
                    source_file="policy.pdf",
                    page_number=1,
                    chunk_id="policy.pdf-p1-c1",
                    document_type="pdf",
                ),
            )
        ]
        store.add_chunks(chunks_v3, [[0.1, 0.2, 0.3]])
        WorkspaceService.update_hash(username, "hash3", "policy.pdf")

        # Verify: only V3 chunk remains, no orphaned vectors, hash registry stays consistent
        stored_final = store.collection.get(where={"source_file": "policy.pdf"})
        assert len(stored_final["ids"]) == 1
        assert stored_final["ids"] == ["policy.pdf-p1-c1"]
        assert stored_final["documents"] == ["Chunk 1 content V3"]
        assert WorkspaceService.load_hashes(username) == {"hash3": "policy.pdf"}
