
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from app.config import settings as app_settings
from app.retrieval.bm25_index_manager import BM25IndexManager
from app.services.index_maintenance_service import IndexMaintenanceService


@contextmanager
def override_settings(**kwargs):
    """Context manager to temporarily override global Settings singleton values."""
    originals = {k: getattr(app_settings, k) for k in kwargs}
    try:
        for k, v in kwargs.items():
            object.__setattr__(app_settings, k, v)
        yield
    finally:
        for k, v in originals.items():
            object.__setattr__(app_settings, k, v)


class MockSentenceTransformer:
    """Mock SentenceTransformer model for fast, network-free tests."""

    def __init__(self, model_name: str, *args, **kwargs) -> None:
        self.model_name = model_name

    def encode(
        self,
        texts: list[str],
        batch_size: int = 32,
        convert_to_numpy: bool = True,
        show_progress_bar: bool = False,
    ) -> list[list[float]]:
        return [[0.1] * 8 for _ in range(len(texts))]


def test_index_rebuild_workflow(tmp_path: Path) -> None:
    username = "admin"

    # Setup Admin upload directories
    user_upload_dir = tmp_path / "uploads" / username
    user_upload_dir.mkdir(parents=True, exist_ok=True)

    file1 = user_upload_dir / "policy.txt"
    file1.write_text("Company standard leave policy guidelines.", encoding="utf-8")

    with (
        override_settings(
            data_dir=tmp_path,
            upload_dir=tmp_path / "uploads",
            chroma_db_dir=tmp_path / "chroma",
            chroma_collection_name="test_collection",
            allowed_upload_extensions=("pdf", "txt"),
            embedding_model_name="mock-model",
            embedding_dimension=8,
            embedding_batch_size=32,
            semantic_top_k=5,
            bm25_top_k=5,
            rrf_k=60,
            retrieval_top_k=3,
            retrieval_min_similarity=0.3,
            enable_hybrid_search=True,
        ),
        patch(
            "app.services.index_maintenance_service.SentenceTransformer",
            MockSentenceTransformer,
        ),
    ):

        bm25_manager = BM25IndexManager(
            username=username, storage_dir=tmp_path / "bm25_index" / username
        )

        # Run rebuild
        summary = IndexMaintenanceService.rebuild_indexes(
            username=username,
            bm25_index_manager=bm25_manager,
        )

        # Verify success
        assert "policy.txt" in summary["processed_documents"]
        assert summary["total_chunks"] == 1
        assert len(summary["failed_files"]) == 0

        # Search retrieved successfully
        results = bm25_manager.search("policy", top_k=1)
        assert len(results) == 1
        assert "policy.txt" in results[0].metadata.source_file


def test_index_rebuild_empty_workspace(tmp_path: Path) -> None:
    username = "empty_user"

    user_upload_dir = tmp_path / "uploads" / username
    user_upload_dir.mkdir(parents=True, exist_ok=True)

    with (
        override_settings(
            data_dir=tmp_path,
            upload_dir=tmp_path / "uploads",
            chroma_db_dir=tmp_path / "chroma",
            chroma_collection_name="test_collection",
            allowed_upload_extensions=("pdf", "txt"),
            embedding_model_name="mock-model",
            embedding_dimension=8,
            embedding_batch_size=32,
            semantic_top_k=5,
            bm25_top_k=5,
            rrf_k=60,
            retrieval_top_k=3,
            retrieval_min_similarity=0.3,
            enable_hybrid_search=True,
        ),
        patch(
            "app.services.index_maintenance_service.SentenceTransformer",
            MockSentenceTransformer,
        ),
    ):

        bm25_manager = BM25IndexManager(
            username=username, storage_dir=tmp_path / "bm25_index" / username
        )

        # Run rebuild
        summary = IndexMaintenanceService.rebuild_indexes(
            username=username,
            bm25_index_manager=bm25_manager,
        )

        # Graceful exit with 0 processed documents
        assert len(summary["processed_documents"]) == 0
        assert summary["total_chunks"] == 0


def test_index_rebuild_corrupted_corpus_recovery(tmp_path: Path) -> None:
    username = "corrupt_user"
    user_upload_dir = tmp_path / "uploads" / username
    user_upload_dir.mkdir(parents=True, exist_ok=True)

    file1 = user_upload_dir / "policy.txt"
    file1.write_text("Standard leave policy document content.", encoding="utf-8")

    bm25_dir = tmp_path / "bm25_index" / username
    bm25_dir.mkdir(parents=True, exist_ok=True)
    corpus_file = bm25_dir / "corpus.json"
    corpus_file.write_text("{invalid json: {corrupt", encoding="utf-8")

    with (
        override_settings(
            data_dir=tmp_path,
            upload_dir=tmp_path / "uploads",
            chroma_db_dir=tmp_path / "chroma",
            chroma_collection_name="test_collection",
            allowed_upload_extensions=("pdf", "txt"),
            embedding_model_name="mock-model",
            embedding_dimension=8,
            embedding_batch_size=32,
            semantic_top_k=5,
            bm25_top_k=5,
            rrf_k=60,
            retrieval_top_k=3,
            retrieval_min_similarity=0.3,
            enable_hybrid_search=True,
        ),
        patch(
            "app.services.index_maintenance_service.SentenceTransformer",
            MockSentenceTransformer,
        ),
    ):

        bm25_manager = BM25IndexManager(username=username, storage_dir=bm25_dir)

        # Load corrupted file first (will log error and clear states)
        bm25_manager.load()
        assert len(bm25_manager._chunk_ids) == 0

        # Run rebuild to heal/overwrite the corrupted JSON
        summary = IndexMaintenanceService.rebuild_indexes(
            username=username,
            bm25_index_manager=bm25_manager,
        )

        assert "policy.txt" in summary["processed_documents"]
        # Verify JSON is repaired and readable
        bm25_manager.load()
        assert len(bm25_manager._chunk_ids) == 1


def test_index_rebuild_workspace_isolation(tmp_path: Path) -> None:
    # Set up files for both admin and varshini
    for user in ("admin", "varshini"):
        user_dir = tmp_path / "uploads" / user
        user_dir.mkdir(parents=True, exist_ok=True)
        file = user_dir / f"{user}_policy.txt"
        file.write_text(f"Policy document for {user}.", encoding="utf-8")

    with (
        override_settings(
            data_dir=tmp_path,
            upload_dir=tmp_path / "uploads",
            chroma_db_dir=tmp_path / "chroma",
            chroma_collection_name="test_collection",
            allowed_upload_extensions=("pdf", "txt"),
            embedding_model_name="mock-model",
            embedding_dimension=8,
            embedding_batch_size=32,
            semantic_top_k=5,
            bm25_top_k=5,
            rrf_k=60,
            retrieval_top_k=3,
            retrieval_min_similarity=0.3,
            enable_hybrid_search=True,
        ),
        patch(
            "app.services.index_maintenance_service.SentenceTransformer",
            MockSentenceTransformer,
        ),
    ):

        # Rebuild only admin
        bm25_admin = BM25IndexManager(
            username="admin", storage_dir=tmp_path / "bm25_index" / "admin"
        )
        summary_admin = IndexMaintenanceService.rebuild_indexes(
            username="admin",
            bm25_index_manager=bm25_admin,
        )

        # Verify admin rebuilt
        assert "admin_policy.txt" in summary_admin["processed_documents"]

        # Verify varshini remains untouched (no index file created yet for varshini)
        varshini_corpus = tmp_path / "bm25_index" / "varshini" / "corpus.json"
        assert not varshini_corpus.exists()
