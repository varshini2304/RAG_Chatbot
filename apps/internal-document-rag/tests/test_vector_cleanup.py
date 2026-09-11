"""Unit and integration tests for ChromaDB vector cleanup operations."""

from __future__ import annotations

from pathlib import Path

from app.models.schemas import ChunkMetadata, DocumentChunk
from app.vectorstore.chroma_manager import ChromaVectorStore


def _chunk(
    filename: str, chunk_id: str, content: str = "Sample content"
) -> DocumentChunk:
    return DocumentChunk(
        content=content,
        metadata=ChunkMetadata(
            source_file=filename,
            page_number=1,
            chunk_id=chunk_id,
            document_type="pdf",
        ),
    )


def test_clear_workspace_removes_all_chunks(tmp_path: Path) -> None:
    """ChromaDB collection count should become zero after clear_workspace."""
    store = ChromaVectorStore(
        persist_directory=tmp_path / "chroma",
        collection_name="test_clear_workspace",
    )

    chunks = [
        _chunk("doc1.pdf", "doc1-c1"),
        _chunk("doc1.pdf", "doc1-c2"),
        _chunk("doc2.pdf", "doc2-c1"),
    ]
    embeddings = [[0.1] * 384, [0.2] * 384, [0.3] * 384]

    store.add_chunks(chunks, embeddings)
    assert store.collection.count() == 3

    # Clear workspace
    store.clear_workspace()
    assert store.collection.count() == 0


def test_delete_document_removes_only_specific_document_chunks(tmp_path: Path) -> None:
    """delete_document should delete chunks matching source_file and leave others."""
    store = ChromaVectorStore(
        persist_directory=tmp_path / "chroma",
        collection_name="test_delete_document",
    )

    chunks = [
        _chunk("doc1.pdf", "doc1-c1"),
        _chunk("doc1.pdf", "doc1-c2"),
        _chunk("doc2.pdf", "doc2-c1"),
    ]
    embeddings = [[0.1] * 384, [0.2] * 384, [0.3] * 384]

    store.add_chunks(chunks, embeddings)
    assert store.collection.count() == 3

    # Delete doc1
    store.delete_document("doc1.pdf")

    # Verify only doc2 remains
    assert store.collection.count() == 1
    remaining = store.collection.get()
    assert remaining["ids"] == ["doc2-c1"]
    assert remaining["metadatas"][0]["source_file"] == "doc2.pdf"


def test_upload_delete_upload_cycle_has_no_duplicates(tmp_path: Path) -> None:
    """No duplicate vectors should remain after upload -> delete -> upload cycle."""
    store = ChromaVectorStore(
        persist_directory=tmp_path / "chroma",
        collection_name="test_upload_delete_upload",
    )

    # 1. Upload
    chunks_1 = [_chunk("doc1.pdf", "doc1-c1", "Initial version text")]
    embeddings_1 = [[0.1] * 384]
    store.add_chunks(chunks_1, embeddings_1)
    assert store.collection.count() == 1

    # 2. Delete
    store.delete_document("doc1.pdf")
    assert store.collection.count() == 0

    # 3. Upload again (potentially with different content/index)
    chunks_2 = [
        _chunk("doc1.pdf", "doc1-c1", "Updated version text"),
        _chunk("doc1.pdf", "doc1-c2", "Additional chunk"),
    ]
    embeddings_2 = [[0.2] * 384, [0.3] * 384]
    store.add_chunks(chunks_2, embeddings_2)

    # 4. Verify count and records are correct and not duplicated
    assert store.collection.count() == 2
    stored = store.collection.get(include=["documents", "metadatas"])
    assert sorted(stored["ids"]) == ["doc1-c1", "doc1-c2"]
    assert "Updated version text" in stored["documents"]
    assert "Initial version text" not in stored["documents"]
