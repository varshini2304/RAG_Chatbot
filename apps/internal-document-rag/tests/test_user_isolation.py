"""Integration tests verifying user-level workspace isolation and retrieval boundaries."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from app.models.schemas import ChunkMetadata, DocumentChunk
from app.retrieval.retriever import DocumentRetriever
from app.services.workspace_service import WorkspaceService
from app.vectorstore.chroma_manager import ChromaVectorStore


def test_central_sanitization() -> None:
    """Verify central username sanitization and directory helpers."""
    assert WorkspaceService.get_workspace_name("admin") == "admin"
    assert WorkspaceService.get_workspace_name("user name") == "user_name"
    assert WorkspaceService.get_workspace_name("user@domain.com") == "user_domain_com"
    assert WorkspaceService.get_collection_name("admin") == "rag_admin"


def test_hash_registry_isolation(tmp_path) -> None:
    """Verify load/save/update/remove hashes are isolated per user."""
    mock_settings = SimpleNamespace(
        upload_dir=tmp_path / "uploads", allowed_upload_extensions=("pdf", "txt")
    )
    with patch("app.services.workspace_service.settings", mock_settings):
        WorkspaceService.save_hashes("user1", {"hash1": "doc1.txt"})
        WorkspaceService.save_hashes("user2", {"hash2": "doc2.txt"})

        assert WorkspaceService.load_hashes("user1") == {"hash1": "doc1.txt"}
        assert WorkspaceService.load_hashes("user2") == {"hash2": "doc2.txt"}

        WorkspaceService.update_hash("user1", "hash3", "doc3.txt")
        assert WorkspaceService.load_hashes("user1") == {
            "hash1": "doc1.txt",
            "hash3": "doc3.txt",
        }
        assert WorkspaceService.load_hashes("user2") == {"hash2": "doc2.txt"}

        WorkspaceService.remove_hash_for_file("user1", "doc1.txt")
        assert WorkspaceService.load_hashes("user1") == {"hash3": "doc3.txt"}


def test_workspace_isolation_and_retrieval(tmp_path) -> None:
    """Verify retrieval only accesses the current user's collection."""
    mock_settings = SimpleNamespace(
        upload_dir=tmp_path / "uploads", allowed_upload_extensions=("pdf", "txt")
    )
    with patch("app.services.workspace_service.settings", mock_settings):
        # User 1 embeds in user1 collection using dependency injection for persist_directory
        user1_store = ChromaVectorStore(
            persist_directory=tmp_path / "chroma",
            collection_name=WorkspaceService.get_collection_name("user1"),
        )
        chunk1 = DocumentChunk(
            content="This is User1 private content",
            metadata=ChunkMetadata(
                source_file="secret1.txt",
                page_number=1,
                chunk_id="user1-c1",
                document_type="txt",
            ),
        )
        user1_store.add_chunks([chunk1], [[0.1] * 384])

        # User 2 embeds in user2 collection using dependency injection
        user2_store = ChromaVectorStore(
            persist_directory=tmp_path / "chroma",
            collection_name=WorkspaceService.get_collection_name("user2"),
        )
        chunk2 = DocumentChunk(
            content="This is User2 private content",
            metadata=ChunkMetadata(
                source_file="secret2.txt",
                page_number=1,
                chunk_id="user2-c1",
                document_type="txt",
            ),
        )
        user2_store.add_chunks([chunk2], [[0.2] * 384])

        # User 1 retrieves and sees ONLY User 1 content
        retriever1 = DocumentRetriever(
            persist_directory=tmp_path / "chroma",
            collection_name=WorkspaceService.get_collection_name("user1"),
        )
        res1 = retriever1.retrieve("User1 private content")
        assert len(res1) == 1
        assert "User1" in res1[0].content

        # User 2 retrieves and sees ONLY User 2 content
        retriever2 = DocumentRetriever(
            persist_directory=tmp_path / "chroma",
            collection_name=WorkspaceService.get_collection_name("user2"),
        )
        res2 = retriever2.retrieve("User2 private content")
        assert len(res2) == 1
        assert "User2" in res2[0].content
