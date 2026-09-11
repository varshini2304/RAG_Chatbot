"""Unit tests for IndexMaintenanceService rebuild orchestration."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from app.config import settings as app_settings
from app.retrieval.bm25_index_manager import BM25IndexManager
from app.services.index_maintenance_service import IndexMaintenanceService


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


class MockSentenceTransformer:

    def __init__(self, model_name: str, *args, **kwargs) -> None:
        self.model_name = model_name

    def encode(
        self,
        texts: list[str],
        batch_size: int = 32,
        convert_to_numpy: bool = True,
        show_progress_bar: bool = False,
    ) -> list[list[float]]:
        dim = app_settings.embedding_dimension
        return [[0.1] * dim for _ in range(len(texts))]


def test_index_rebuild_orchestration(tmp_path: Path) -> None:
    username = "rebuild_test_user"

    # 1. Setup mock upload directories
    user_upload_dir = tmp_path / "uploads" / username
    user_upload_dir.mkdir(parents=True, exist_ok=True)

    # Create two dummy TXT files
    file1 = user_upload_dir / "policy_doc.txt"
    file1.write_text(
        "Vanguard asset management policy for detroit facility.", encoding="utf-8"
    )

    file2 = user_upload_dir / "leave_doc.txt"
    file2.write_text(
        "Aetheris company leaves and annual paid holidays details.", encoding="utf-8"
    )

    # Override settings dynamically and run rebuild
    with (
        override_settings(
            data_dir=tmp_path,
            upload_dir=tmp_path / "uploads",
            chroma_db_dir=tmp_path / "chroma",
            chroma_collection_name="test_collection",
            allowed_upload_extensions=("pdf", "txt"),
            embedding_model_name="mock-model",
            embedding_dimension=8,  # Keep it small for mock test
            embedding_batch_size=32,
            semantic_top_k=10,
            bm25_top_k=10,
            rrf_k=60,
            retrieval_top_k=5,
            retrieval_min_similarity=0.3,
            enable_hybrid_search=True,
        ),
        patch(
            "app.services.index_maintenance_service.SentenceTransformer",
            MockSentenceTransformer,
        ),
    ):

        # Initialize BM25 index manager
        bm25_manager = BM25IndexManager(
            username=username, storage_dir=tmp_path / "bm25_index" / username
        )

        # Run rebuild
        summary = IndexMaintenanceService.rebuild_indexes(
            username=username,
            bm25_index_manager=bm25_manager,
        )

        # 2. Verify summary output
        assert len(summary["processed_documents"]) == 2
        assert "policy_doc.txt" in summary["processed_documents"]
        assert "leave_doc.txt" in summary["processed_documents"]
        assert summary["total_chunks"] > 0
        assert len(summary["failed_files"]) == 0

        # 3. Verify in-memory BM25 states
        assert len(bm25_manager._chunk_ids) == summary["total_chunks"]
        assert bm25_manager._bm25 is not None

        # Verify search retrieves correct results
        results = bm25_manager.search("Vanguard", top_k=1)
        assert len(results) == 1
        assert "policy_doc.txt" in results[0].metadata.source_file

        # Verify plain JSON file exists
        assert (tmp_path / "bm25_index" / username / "corpus.json").exists()
