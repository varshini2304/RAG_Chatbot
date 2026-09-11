"""Unit tests verifying embedding dimension guards, migration paths, and error states."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest

from app.config import settings as app_settings
from app.retrieval.bm25_index_manager import BM25IndexManager
from app.retrieval.retrieval_engine import RetrievalEngine, RetrievalService
from app.services.index_maintenance_service import IndexMaintenanceService
from app.vectorstore.collection_guard import EmbeddingDimensionMismatchError


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
    """Mock SentenceTransformer returning vectors matching current Settings dimension."""

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


def test_full_migration_flow_384_to_1024(tmp_path: Path) -> None:
    username = "migration_user"

    # 1. Setup mock upload files
    user_upload_dir = tmp_path / "uploads" / username
    user_upload_dir.mkdir(parents=True, exist_ok=True)
    file = user_upload_dir / "policy.txt"
    file.write_text(
        "Company guidelines on educational reimbursement limit.", encoding="utf-8"
    )

    # Create the old 384-dimension collection
    with (
        override_settings(
            data_dir=tmp_path,
            upload_dir=tmp_path / "uploads",
            chroma_db_dir=tmp_path / "chroma",
            chroma_collection_name="migration_test_collection",
            allowed_upload_extensions=("pdf", "txt"),
            embedding_model_name="old-384-model",
            embedding_dimension=384,
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

        # Ingest a document chunk using 384 dimensions
        bm25 = BM25IndexManager(
            username=username, storage_dir=tmp_path / "bm25_index" / username
        )

        IndexMaintenanceService.rebuild_indexes(
            username=username,
            bm25_index_manager=bm25,
        )

        # Verify collection has metadata dimension 384
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        client = chromadb.PersistentClient(
            path=str(tmp_path / "chroma"),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        collection = client.get_collection(name="migration_test_collection")
        assert collection.metadata.get("embedding_dimension") == 384

    with (
        override_settings(
            data_dir=tmp_path,
            upload_dir=tmp_path / "uploads",
            chroma_db_dir=tmp_path / "chroma",
            chroma_collection_name="migration_test_collection",
            allowed_upload_extensions=("pdf", "txt"),
            embedding_model_name="new-1024-model",
            embedding_dimension=1024,
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
        patch("app.retrieval.retrieval_engine.detect_language", return_value="en"),
    ):

        with pytest.raises(EmbeddingDimensionMismatchError) as exc_info:
            RetrievalService(bm25_index_manager=bm25)

        assert "dimension mismatch: stored=384, configured=1024" in str(exc_info.value)

        summary = IndexMaintenanceService.rebuild_indexes(
            username=username,
            bm25_index_manager=bm25,
        )
        assert summary["total_chunks"] == 1

        # Verify collection metadata updated to 1024
        client = chromadb.PersistentClient(
            path=str(tmp_path / "chroma"),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        collection = client.get_collection(name="migration_test_collection")
        assert collection.metadata.get("embedding_dimension") == 1024

        retrieval = RetrievalService(bm25_index_manager=bm25)
        results = retrieval.search("guidelines", top_k=1)
        assert len(results) == 1
        assert "policy.txt" in results[0].metadata.source_file
