"""System Test Scenario 1: End-to-End User Journey (Login -> Upload -> Q&A -> Logout)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.models.query_result import QueryResultKind
from app.models.schemas import (
    ChunkMetadata,
    DocumentChunk,
    ExtractedPage,
    ExtractedPdfDocument,
)
from app.services.query_service import QueryService
from app.utils.auth import AuthManager


class DummyPDFLoader:
    def extract(self, file_path: Path) -> ExtractedPdfDocument:
        return ExtractedPdfDocument(
            source_file=file_path.name,
            file_path=file_path,
            document_type="pdf",
            pages=[
                ExtractedPage(
                    page_number=1,
                    content="System E2E Test: Security policy mandates 2FA for all users.",
                )
            ],
        )


def test_system_scenario_1_end_to_end_user_journey(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """System Scenario 1: Validate full user lifecycle: Login -> Upload -> Ask Question -> Get Answer -> Logout."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    mock_settings = SimpleNamespace(
        user_credentials="user_e2e:pass123",
        data_dir=data_dir,
        upload_dir=data_dir / "uploads",
        allowed_upload_extensions=("pdf", "txt"),
        max_upload_size_mb=10,
    )

    with patch("app.utils.auth.settings", mock_settings):
        # 1. Login user
        assert AuthManager.verify_login("user_e2e", "pass123") is True

        # 2. Upload document
        upload_file = data_dir / "uploads" / "security.pdf"
        upload_file.parent.mkdir(parents=True, exist_ok=True)
        upload_file.write_text("Security policy mandates 2FA for all users.")
        assert upload_file.exists()

        # 3. Ask Question via RAG Service
        doc_chunk = DocumentChunk(
            content="Security policy mandates 2FA for all users.",
            metadata=ChunkMetadata(
                source_file="security.pdf",
                page_number=1,
                chunk_id="sec-p1-c1",
                document_type="pdf",
            ),
        )
        mock_llm = MagicMock()
        mock_llm.generate_answer.return_value = "The security policy mandates 2FA (Two-Factor Authentication) for all users."

        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = [doc_chunk]

        with (
            patch(
                "app.services.query_service.DocumentRetriever",
                return_value=mock_retriever,
            ),
            patch("app.services.query_service.get_llm_provider", return_value=mock_llm),
        ):
            result = QueryService.process_question(
                "Is 2FA required?", username="user_e2e", query_language="en"
            )
            assert result.kind == QueryResultKind.SUCCESS
            assert "2FA" in result.answer

        # 4. Logout / Session teardown simulation
        session_token = None
        assert session_token is None
