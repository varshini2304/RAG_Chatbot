"""Unit tests for Analytics repository and log processing services."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.api.repositories.analytics_repository import AnalyticsRepository
from app.api.services.analytics_service import AnalyticsService


def test_analytics_repository_parses_provider_shares(tmp_path: Path) -> None:
    """AnalyticsRepository should parse app.log and compute accurate LLM provider distribution shares."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"

    log_content = (
        "2026-07-23 10:00:00 - app.llm.groq_provider - INFO - Response successfully generated using groq\n"
        "2026-07-23 10:01:00 - app.llm.groq_provider - INFO - Response successfully generated using groq\n"
        "2026-07-23 10:02:00 - app.llm.ollama_provider - INFO - Response successfully generated using ollama\n"
        "2026-07-23 10:03:00 - pytest - INFO - Test log entry that should be excluded\n"
    )
    log_file.write_text(log_content, encoding="utf-8")

    mock_settings = SimpleNamespace(data_dir=tmp_path, primary_provider="groq")
    with (
        patch("app.api.repositories.analytics_repository.settings", mock_settings),
        patch(
            "app.utils.logger.InMemoryLogBufferHandler.get_instance"
        ) as mock_mem_handler,
    ):

        mock_mem_handler.return_value.get_logs.return_value = []

        repo = AnalyticsRepository()
        shares = repo.get_provider_shares()

        groq_share = next((s for s in shares if "groq" in s["name"].lower()), None)
        ollama_share = next((s for s in shares if "ollama" in s["name"].lower()), None)

        assert groq_share is not None
        assert groq_share["value"] == 2

        assert ollama_share is not None
        assert ollama_share["value"] == 1


def test_analytics_service_compiles_data() -> None:
    """AnalyticsService should combine repository queries into a unified payload."""
    with patch(
        "app.api.services.analytics_service.AnalyticsRepository"
    ) as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_trend_analytics.return_value = [
            {"date": "2026-07-23", "groq": 10, "gemini": 0, "ollama": 1}
        ]
        mock_repo.get_provider_shares.return_value = [
            {"name": "Groq Cloud", "value": 10, "color": "#000", "percentage": "90.0%"}
        ]
        mock_repo.get_conversation_counts.return_value = {
            "total_conversations": 11,
            "avg_response_time_sec": 1.2,
        }

        service = AnalyticsService()
        data = service.get_analytics()

        assert data.total_queries == 11
        assert len(data.provider_shares) == 1
        assert data.provider_shares[0].name == "Groq Cloud"
