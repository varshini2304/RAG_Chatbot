
from __future__ import annotations

from dataclasses import replace
from unittest.mock import patch

import pytest
import requests

from app.config import settings
from app.llm.base_provider import BaseLLMProvider
from app.llm.exceptions import LLMProviderError
from app.llm.llm_router import LLMRouter
from app.llm.ollama_provider import OllamaProvider


class MockProvider(BaseLLMProvider):
    def __init__(
        self,
        provider_name: str,
        model_name: str,
        should_fail: bool = False,
        answer: str = "Mock Answer",
    ) -> None:
        self._provider_name = provider_name
        self._model_name = model_name
        self.should_fail = should_fail
        self.answer = answer
        self.calls = 0

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate_answer(
        self, question: str, context: str, query_language: str = "en"
    ) -> str:
        self.calls += 1
        if self.should_fail:
            raise LLMProviderError(f"{self._provider_name} simulated failure")
        return self.answer

    def check_health(self) -> bool:
        return not self.should_fail


def _router_settings():
    return replace(
        settings,
        primary_provider="groq",
        secondary_provider="gemini",
        tertiary_provider="ollama",
    )


def test_router_groq_success_no_fallback():
    router = LLMRouter()
    mock_groq = MockProvider("groq", "llama-3.3-70b-versatile", answer="Groq Response")
    mock_gemini = MockProvider("gemini", "gemini-2.5-flash")
    mock_ollama = MockProvider("ollama", "qwen2.5:3b")

    router._groq_provider = mock_groq
    router._gemini_provider = mock_gemini
    router._ollama_provider = mock_ollama

    with patch("app.llm.llm_router.settings", _router_settings()):
        ans = router.generate_answer("What is RAG?", "Dummy Context")
    assert ans == "Groq Response"
    assert mock_groq.calls == 1
    assert mock_gemini.calls == 0
    assert mock_ollama.calls == 0
    assert router.provider_name == "Groq"
    assert router.model_name == "llama-3.3-70b-versatile"


def test_router_groq_failure_gemini_success():
    router = LLMRouter()
    mock_groq = MockProvider("groq", "llama-3.3-70b-versatile", should_fail=True)
    mock_gemini = MockProvider("gemini", "gemini-2.5-flash", answer="Gemini Response")
    mock_ollama = MockProvider("ollama", "qwen2.5:3b")

    router._groq_provider = mock_groq
    router._gemini_provider = mock_gemini
    router._ollama_provider = mock_ollama

    with patch("app.llm.llm_router.settings", _router_settings()):
        ans = router.generate_answer("What is RAG?", "Dummy Context")
    assert ans == "Gemini Response"
    assert mock_groq.calls == 1
    assert mock_gemini.calls == 1
    assert mock_ollama.calls == 0
    assert router.provider_name == "Gemini"
    assert router.model_name == "gemini-2.5-flash"


def test_router_groq_and_gemini_failure_ollama_success():
    router = LLMRouter()
    mock_groq = MockProvider("groq", "llama-3.3-70b-versatile", should_fail=True)
    mock_gemini = MockProvider("gemini", "gemini-2.5-flash", should_fail=True)
    mock_ollama = MockProvider("ollama", settings.ollama_model, answer="Ollama Response")

    router._groq_provider = mock_groq
    router._gemini_provider = mock_gemini
    router._ollama_provider = mock_ollama

    with patch("app.llm.llm_router.settings", _router_settings()):
        ans = router.generate_answer("What is RAG?", "Dummy Context")
    assert ans == "Ollama Response"
    assert mock_groq.calls == 1
    assert mock_gemini.calls == 1
    assert mock_ollama.calls == 1
    assert router.provider_name == "Ollama"
    assert router.model_name == settings.ollama_model


def test_router_all_providers_unavailable():
    router = LLMRouter()
    mock_groq = MockProvider("groq", "llama-3.3-70b-versatile", should_fail=True)
    mock_gemini = MockProvider("gemini", "gemini-2.5-flash", should_fail=True)
    mock_ollama = MockProvider("ollama", "qwen2.5:3b", should_fail=True)

    router._groq_provider = mock_groq
    router._gemini_provider = mock_gemini
    router._ollama_provider = mock_ollama

    with (
        patch("app.llm.llm_router.settings", _router_settings()),
        pytest.raises(LLMProviderError) as exc_info,
    ):
        router.generate_answer("What is RAG?", "Dummy Context")
    assert "⚠️ Chatbot is currently unavailable. Please try again later." in str(
        exc_info.value
    )


def test_circuit_breaker_trips_and_skips_provider():
    router = LLMRouter()
    mock_groq = MockProvider("groq", "llama-3.3-70b-versatile", should_fail=True)
    mock_gemini = MockProvider("gemini", "gemini-2.5-flash", answer="Gemini Response")
    mock_ollama = MockProvider("ollama", "qwen2.5:3b")

    router._groq_provider = mock_groq
    router._gemini_provider = mock_gemini
    router._ollama_provider = mock_ollama

    mock_settings = replace(
        _router_settings(), circuit_breaker_threshold=2, circuit_breaker_cooldown=60
    )
    with patch("app.llm.llm_router.settings", mock_settings):
        # 1st failure of Groq
        router.generate_answer("What is RAG?", "Dummy Context")
        assert mock_groq.calls == 1
        assert mock_gemini.calls == 1

        # 2nd failure of Groq (trips the circuit breaker)
        mock_groq.calls = 0
        mock_gemini.calls = 0
        router.generate_answer("What is RAG?", "Dummy Context")
        assert mock_groq.calls == 1
        assert mock_gemini.calls == 1

        # 3rd attempt: Groq is OPEN and must be SKIPPED directly
        mock_groq.calls = 0
        mock_gemini.calls = 0
        router.generate_answer("What is RAG?", "Dummy Context")
        assert mock_groq.calls == 0  # Groq was skipped!
        assert mock_gemini.calls == 1


def test_ollama_provider_retries_on_timeout():
    provider = OllamaProvider(
        base_url="http://localhost:11434", model_name="qwen2.5:3b"
    )

    with (
        patch(
            "requests.post",
            side_effect=requests.exceptions.Timeout("Simulated timeout"),
        ),
        patch("tenacity.nap.time.sleep", return_value=None),
    ):
        with pytest.raises(LLMProviderError) as exc_info:
            provider.generate_answer("What is RAG?", "Dummy Context")
        assert "Ollama answer generation timed out." in str(exc_info.value)


def test_select_highest_priority_provider_health_check():
    router = LLMRouter()
    mock_groq = MockProvider("groq", "llama-3.3-70b-versatile", should_fail=True)
    mock_gemini = MockProvider("gemini", "gemini-2.5-flash", should_fail=True)
    mock_ollama = MockProvider("ollama", "model", should_fail=False)

    router._groq_provider = mock_groq
    router._gemini_provider = mock_gemini
    router._ollama_provider = mock_ollama

    # Case 1: Groq healthy -> selects groq
    mock_groq.should_fail = False
    with patch("app.llm.llm_router.settings", _router_settings()):
        active = router.select_highest_priority_provider()
    assert active == "groq"

    # Case 2: Groq down, Gemini healthy -> selects gemini
    mock_groq.should_fail = True
    mock_gemini.should_fail = False
    with patch("app.llm.llm_router.settings", _router_settings()):
        active = router.select_highest_priority_provider()
    assert active == "gemini"

    # Case 3: Groq & Gemini down, Ollama healthy -> selects ollama
    mock_gemini.should_fail = True
    mock_ollama.should_fail = False
    with patch("app.llm.llm_router.settings", _router_settings()):
        active = router.select_highest_priority_provider()
    assert active == "ollama"

    # Case 4: All down -> selects None
    mock_ollama.should_fail = True
    with patch("app.llm.llm_router.settings", _router_settings()):
        active = router.select_highest_priority_provider()
    assert active == "None"


def test_active_state_snapshot_tracks_real_failover_provider():
    router = LLMRouter()
    mock_groq = MockProvider("groq", "llama-3.3-70b-versatile", should_fail=True)
    mock_gemini = MockProvider("gemini", "gemini-2.5-flash", answer="Gemini Response")
    mock_ollama = MockProvider("ollama", "qwen2.5:3b")

    router._groq_provider = mock_groq
    router._gemini_provider = mock_gemini
    router._ollama_provider = mock_ollama

    with patch("app.llm.llm_router.settings", _router_settings()):
        ans = router.generate_answer("What is RAG?", "Dummy Context")
    assert ans == "Gemini Response"

    snapshot = router.get_active_state_snapshot()
    assert snapshot["initialized"] is True
    assert snapshot["provider"] == "Gemini"
    assert snapshot["model"] == "gemini-2.5-flash"
    assert snapshot["fallback_active"] is True
    assert snapshot["offline_mode"] is False
    assert snapshot["fallback_active"] is True
    assert snapshot["offline_mode"] is False
