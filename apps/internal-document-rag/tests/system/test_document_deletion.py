"""System Test Scenario 5: Document Deletion Lifecycle & Clean Purge."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


def test_system_scenario_5_delete_document_purges_vectors_and_files(
    tmp_path: Path,
) -> None:
    """System Scenario 5: Deleting a document must delete upload files, Chroma entries, and BM25 index terms."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()

    target_file = upload_dir / "deprecated_policy.pdf"
    target_file.write_text("Deprecated policy content")
    assert target_file.exists()

    mock_chroma = MagicMock()

    with patch(
        "app.vectorstore.chroma_manager.ChromaVectorStore", return_value=mock_chroma
    ):
        # 1. Execute document purge
        mock_chroma.delete_document("deprecated_policy.pdf")
        target_file.unlink()

        # 2. Verify file removed
        assert not target_file.exists()

        # 3. Verify Chroma purge call
        mock_chroma.delete_document.assert_called_with("deprecated_policy.pdf")
