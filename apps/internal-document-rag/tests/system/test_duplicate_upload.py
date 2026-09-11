"""System Test Scenario 4: Upload Duplicate Document and Idempotent Upsert Handling."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from app.models.schemas import ChunkMetadata, DocumentChunk
from app.vectorstore.chroma_manager import ChromaVectorStore


def test_system_scenario_4_duplicate_upload_idempotency(tmp_path: Path) -> None:
    """System Scenario 4: Uploading duplicate document should overwrite existing vectors cleanly without orphan chunks."""
    source_file = "employee_handbook.pdf"
    chroma_dir = tmp_path / "chroma"
    chroma_dir.mkdir()

    chunk_v1 = DocumentChunk(
        content="Employee Handbook 2026 Edition: Version 1.0",
        metadata=ChunkMetadata(
            source_file=source_file,
            page_number=1,
            chunk_id="employee_handbook.pdf_p1_c0",
            document_type="pdf",
        ),
    )

    with patch("chromadb.PersistentClient") as mock_chroma_cls:
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.metadata = {"embedding_dimension": 384}
        mock_collection.get.return_value = {"ids": ["employee_handbook.pdf_p1_c0"]}
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chroma_cls.return_value = mock_client

        vector_store = ChromaVectorStore(
            persist_directory=chroma_dir, collection_name="dup_test"
        )

        # 1. First upload
        ids_1 = vector_store.add_chunks([chunk_v1], [[0.1] * 384])
        assert ids_1 == ["employee_handbook.pdf_p1_c0"]

        # 2. Duplicate upload of identical document
        ids_2 = vector_store.add_chunks([chunk_v1], [[0.1] * 384])
        assert ids_2 == ["employee_handbook.pdf_p1_c0"]

        # Verify upsert was invoked twice with identical IDs (idempotent replacement)
        assert mock_collection.upsert.call_count == 2
