"""Unit tests for LLM providers, LLM router fallback, and prompt builder."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.llm.gemini_provider import GeminiProvider
from app.llm.groq_provider import GroqProvider
from app.llm.llm_router import LLMRouter
from app.llm.ollama_provider import OllamaProvider
from app.llm.prompt_builder import PromptBuilder


def test_prompt_builder_constructs_rag_prompt() -> None:
    """PromptBuilder should inject question, context, and language into prompt template."""
    prompt = PromptBuilder.build_rag_prompt(
        question="What is the vacation policy?",
        context="Employees get 20 paid vacation days per year.",
        query_language="en",
    )
    assert "What is the vacation policy?" in prompt
    assert "Employees get 20 paid vacation days per year." in prompt
    assert "Do NOT refuse to answer merely because the question is concise or broad." in prompt


def test_groq_provider_missing_api_key_raises_error() -> None:
    """Initializing GroqProvider without an API key must raise ValueError."""
    with pytest.raises(ValueError, match="GROQ_API_KEY is required"):
        GroqProvider(api_key="", model_name="llama-3.3-70b-versatile")


def test_gemini_provider_missing_api_key_raises_error() -> None:
    """Initializing GeminiProvider without an API key must raise ValueError."""
    with pytest.raises(ValueError, match="GOOGLE_API_KEY is required"):
        GeminiProvider(api_key="", model_name="gemini-2.5-flash")


def test_ollama_provider_missing_url_raises_error() -> None:
    """Initializing OllamaProvider without a base URL must raise ValueError."""
    with pytest.raises(ValueError, match="Ollama base URL is required"):
        OllamaProvider(base_url="", model_name="qwen2.5:3b")


def test_llm_router_circuit_breaker_transitions() -> None:
    """LLMRouter should trip circuit breaker on consecutive failures and skip open providers."""
    router = LLMRouter()
    assert router.is_circuit_open("groq") is False

    # Simulate failures reaching threshold (2)
    router.record_failure("groq")
    router.record_failure("groq")

    assert router.is_circuit_open("groq") is True

    # Record success should reset failure count
    router.record_success("groq")
    assert router.is_circuit_open("groq") is False


def test_llm_router_fails_over_to_next_available_provider() -> None:
    """When Groq fails, LLMRouter should fail over to Gemini or Ollama."""
    router = LLMRouter()

    mock_groq = MagicMock()
    mock_groq.generate_answer.side_effect = RuntimeError("Groq Service Unavailable")

    mock_gemini = MagicMock()
    mock_gemini.generate_answer.return_value = "Answer generated via Gemini fallback"

    router._groq_provider = mock_groq
    router._gemini_provider = mock_gemini

    answer = router.generate_answer(
        question="How to request leave?", context="Leave context"
    )
    assert isinstance(answer, str)
