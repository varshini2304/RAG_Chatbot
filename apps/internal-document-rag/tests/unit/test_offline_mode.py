"""Unit tests for Task 4 — Offline mode enforcement and routing guarantees."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.llm.exceptions import LLMProviderError
from app.llm.llm_router import LLMRouter
from app.services.query_service import QueryService
from app.api.schemas.chat import ChatQueryRequest


def test_llm_router_refuses_groq_and_gemini_in_offline_mode():
    """With offline_mode active, LLMRouter._get_provider must raise LLMProviderError for groq/gemini."""
    router = LLMRouter()
    router.set_offline_mode(True)

    with pytest.raises(LLMProviderError, match="Offline Mode Active"):
        router._get_provider("groq")

    with pytest.raises(LLMProviderError, match="Offline Mode Active"):
        router._get_provider("gemini")


def test_llm_router_generate_answer_uses_only_ollama_in_offline_mode():
    """In offline mode, generate_answer must only attempt Ollama and raise error if Ollama fails."""
    router = LLMRouter()
    router.set_offline_mode(True)
    mock_ollama = MagicMock()
    mock_ollama.generate_answer.side_effect = RuntimeError("Ollama connection refused")

    with patch.object(router, "_get_provider", return_value=mock_ollama) as mock_get_prov:
        with pytest.raises(LLMProviderError, match="Offline Mode Active"):
            router.generate_answer("question", "context")

        # Must have attempted ONLY 'ollama'
        mock_get_prov.assert_called_once_with("ollama")


def test_llm_router_set_offline_mode_authoritative():
    """set_offline_mode(True) updates active state and returns Ollama as the active provider."""
    router = LLMRouter()
    router.set_offline_mode(True)

    assert router.is_offline_mode_active() is True
    assert router.provider_name == "Ollama"

    router.set_offline_mode(False)
    assert router.is_offline_mode_active() is False


def test_offline_mode_ollama_success():
    """When Offline Mode is active and Ollama succeeds, answer is generated via Ollama."""
    router = LLMRouter()
    router.set_offline_mode(True)

    mock_ollama = MagicMock()
    mock_ollama.generate_answer.return_value = "Ollama response"

    with patch.object(router, "_get_provider", return_value=mock_ollama):
        ans = router.generate_answer("question", "context")
        assert ans == "Ollama response"
        assert router.provider_name == "Ollama"


def test_query_service_accepts_offline_mode():
    """QueryService.process_question passes offline_mode to LLMRouter."""
    from app.models.query_result import QueryResultKind

    with patch("app.services.query_service.get_llm_provider") as mock_get_provider, \
         patch("app.services.query_service.DocumentRetriever") as mock_retriever_cls:
        
        mock_router = MagicMock()
        mock_router.generate_answer.return_value = "Mock answer"
        mock_get_provider.return_value = mock_router

        mock_retriever = MagicMock()
        mock_chunk = MagicMock()
        mock_chunk.content = "relevant content for test question"
        mock_retriever.retrieve.return_value = [mock_chunk]
        mock_retriever_cls.return_value = mock_retriever

        result = QueryService.process_question(
            question="test question",
            username="admin",
            query_language="en",
            offline_mode=True,
        )

        mock_router.set_offline_mode.assert_called_once_with(True)
        assert result.kind == QueryResultKind.SUCCESS
