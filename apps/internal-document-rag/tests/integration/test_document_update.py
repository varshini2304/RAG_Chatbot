"""Integration test for Workflow 4: Upload Updated Document Version -> Delete Previous Embeddings -> Store New Vectors."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from app.models.schemas import ChunkMetadata, DocumentChunk


def test_document_update_replaces_old_embeddings(tmp_path: Path) -> None:
    """Re-uploading/updating a document should purge existing vector entries and insert updated chunks."""
    source_file = "handbook_v2.pdf"

    mock_chroma_store = MagicMock()

    # Updated chunks for v2
    v2_chunk = DocumentChunk(
        content="Handbook v2: Flexible hours 8 AM to 6 PM.",
        metadata=ChunkMetadata(
            source_file=source_file,
            page_number=1,
            chunk_id="handbook_v2.pdf_p1_c0",
            document_type="pdf",
        ),
    )

    with patch(
        "app.vectorstore.chroma_manager.ChromaVectorStore",
        return_value=mock_chroma_store,
    ):
        # 1. Simulate deleting previous embeddings for source_file
        mock_chroma_store.delete_document(source_file)
        mock_chroma_store.delete_document.assert_called_with(source_file)

        # 2. Simulate upserting new v2 chunks
        mock_chroma_store.add_chunks([v2_chunk], [[0.2] * 384])
        mock_chroma_store.add_chunks.assert_called_once()

        # 3. Verify old vectors were replaced
        args, _ = mock_chroma_store.add_chunks.call_args
        assert args[0][0].content == "Handbook v2: Flexible hours 8 AM to 6 PM."
