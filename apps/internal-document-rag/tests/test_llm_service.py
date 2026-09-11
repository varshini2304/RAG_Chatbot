"""Unit tests for ContextBuilder and GeminiProvider (LLM Integration)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.llm.context_builder import ContextBuilder
from app.llm.exceptions import (
    EmptyContextError,
    GeminiProviderError,
    InvalidQueryError,
    ProviderTimeoutError,
)
from app.llm.gemini_provider import GeminiProvider
from app.models.schemas import ChunkMetadata, DocumentChunk


class FakeModels:
    """Test double for the Gemini client's models API."""

    def __init__(
        self, answer: str | None = "Grounded answer.", error: Exception | None = None
    ):
        self.answer = answer
        self.error = error
        self.calls: list[dict[str, str]] = []

    def generate_content(self, *, model: str, contents: str):
        self.calls.append({"model": model, "contents": contents})
        if self.error:
            raise self.error
        mock_response = MagicMock()
        mock_response.text = self.answer
        return mock_response


class FakeClient:
    def __init__(self, models: FakeModels):
        self.models = models


def _chunk(
    content: str = "The objective is to answer questions from internal documents.",
):
    return DocumentChunk(
        content=content,
        metadata=ChunkMetadata(
            source_file="project.pdf",
            page_number=2,
            chunk_id="project.pdf-p2-c1",
            document_type="pdf",
        ),
    )


def test_context_builder_formats_chunks() -> None:
    """ContextBuilder should assemble chunks into a unified string formatted with sources."""
    chunks = [
        _chunk("First chunk content."),
        DocumentChunk(
            content="Second chunk content.",
            metadata=ChunkMetadata(
                source_file="other.txt",
                page_number=1,
                chunk_id="other.txt-p1-c1",
                document_type="txt",
            ),
        ),
    ]
    context = ContextBuilder.build_context(chunks)
    assert "[Context 1]" in context
    assert "Source: project.pdf" in context
    assert "Page: 2" in context
    assert "First chunk content." in context
    assert "[Context 2]" in context
    assert "Source: other.txt" in context
    assert "Page: 1" in context
    assert "Second chunk content." in context


def test_context_builder_rejects_empty_context() -> None:
    """ContextBuilder should raise EmptyContextError on empty lists or blank content chunks."""
    with pytest.raises(EmptyContextError, match="must contain at least one chunk"):
        ContextBuilder.build_context([])

    with pytest.raises(EmptyContextError, match="must contain non-empty content"):
        ContextBuilder.build_context([_chunk("   ")])


def test_generate_answer_uses_context_in_prompt() -> None:
    """GeminiProvider should pass the prompt structured with context and question to genai Client."""
    models = FakeModels(
        answer="The objective is to answer internal document questions."
    )
    client = FakeClient(models)

    with patch("google.genai.Client", return_value=client):
        provider = GeminiProvider(api_key="fake-key", model_name="test-gemini")
        answer = provider.generate_answer(
            "What is the objective?", "Formatted context string."
        )

    assert answer == "The objective is to answer internal document questions."
    assert models.calls[0]["model"] == "test-gemini"
    prompt = models.calls[0]["contents"]
    assert "What is the objective?" in prompt
    assert "Formatted context string." in prompt
    assert "Answer the question using ONLY the information provided" in prompt


@pytest.mark.parametrize("question", ["", "   ", None])
def test_generate_answer_rejects_invalid_query(question) -> None:
    """Questions must be non-empty strings."""
    models = FakeModels()
    client = FakeClient(models)

    with patch("google.genai.Client", return_value=client):
        provider = GeminiProvider(api_key="fake-key", model_name="test-gemini")
        with pytest.raises(InvalidQueryError, match="non-empty string"):
            provider.generate_answer(question, "Some context")


def test_generate_answer_wraps_api_failure() -> None:
    """Gemini API failures should be exposed through GeminiProviderError."""
    models = FakeModels(error=RuntimeError("service unavailable"))
    client = FakeClient(models)

    with patch("google.genai.Client", return_value=client):
        provider = GeminiProvider(api_key="fake-key", model_name="test-gemini")
        with pytest.raises(GeminiProviderError, match="request failed"):
            provider.generate_answer("What is the objective?", "Some context")


def test_generate_answer_handles_timeout() -> None:
    """Timeout failures should use a distinct ProviderTimeoutError."""
    models = FakeModels(error=TimeoutError("request timed out"))
    client = FakeClient(models)

    with patch("google.genai.Client", return_value=client):
        provider = GeminiProvider(api_key="fake-key", model_name="test-gemini")
        with pytest.raises(ProviderTimeoutError, match="timed out"):
            provider.generate_answer("What is the objective?", "Some context")


def test_generate_answer_rejects_empty_response() -> None:
    """A successful API call without answer text is still a generation failure."""
    models = FakeModels(answer="   ")
    client = FakeClient(models)

    with patch("google.genai.Client", return_value=client):
        provider = GeminiProvider(api_key="fake-key", model_name="test-gemini")
        with pytest.raises(GeminiProviderError, match="empty answer"):
            provider.generate_answer("What is the objective?", "Some context")


def test_generate_answer_emits_required_logs(caplog: pytest.LogCaptureFixture) -> None:
    """Generation should log initiation and success."""
    import logging

    logger = logging.getLogger("app.llm.gemini_provider")
    old_propagate = logger.propagate
    logger.propagate = True
    try:
        models = FakeModels()
        client = FakeClient(models)

        with patch("google.genai.Client", return_value=client):
            provider = GeminiProvider(api_key="fake-key", model_name="test-gemini")
            with caplog.at_level("INFO"):
                provider.generate_answer("What is the objective?", "Some context")

        messages = [record.message for record in caplog.records]
        assert any(
            "generating answer via gemini" in message.lower() for message in messages
        )
        assert any(
            "gemini generation succeeded" in message.lower() for message in messages
        )
    finally:
        logger.propagate = old_propagate


def test_gemini_provider_rate_limit_retries_and_raises() -> None:
    """GeminiProvider should retry on ProviderRateLimitError and raise it when retries are exhausted."""
    from app.llm.exceptions import ProviderRateLimitError
    from app.llm.gemini_provider import GeminiProvider

    class MockRateLimitError(Exception):
        status_code = 429

        def __str__(self):
            return "429: Resource has been exhausted (quota exceeded)."

    mock_models = FakeModels(error=MockRateLimitError())
    client = FakeClient(mock_models)

    with patch("google.genai.Client", return_value=client):
        provider = GeminiProvider(api_key="fake-key", model_name="test-gemini")

        with (
            patch("tenacity.nap.time.sleep", return_value=None),
            pytest.raises(ProviderRateLimitError, match="rate limit exceeded"),
        ):
            provider.generate_answer("What is the objective?", "Some context")

    assert len(mock_models.calls) == 3


def test_query_service_surfaces_rate_limit_message() -> None:
    """QueryService should catch ProviderRateLimitError and return the localized message."""
    from app.llm.exceptions import ProviderRateLimitError
    from app.models.query_result import QueryResultKind
    from app.services.query_service import QueryService

    mock_retriever = MagicMock()
    mock_retriever.retrieve.return_value = [
        _chunk("The objective is to answer questions from internal documents.")
    ]

    class MockRateLimitProvider:
        def generate_answer(self, question, context, query_language):
            raise ProviderRateLimitError("Rate limit hit")

    with (
        patch(
            "app.services.query_service.DocumentRetriever", return_value=mock_retriever
        ),
        patch(
            "app.services.query_service.get_llm_provider",
            return_value=MockRateLimitProvider(),
        ),
    ):

        res_en = QueryService.process_question("What is the objective?", "admin", "en")
        assert res_en.kind == QueryResultKind.ERROR
        assert (
            res_en.answer
            == "The AI provider is temporarily rate-limited. Please wait a moment and try again."
        )

        res_ja = QueryService.process_question("What is the objective?", "admin", "ja")
        assert res_ja.kind == QueryResultKind.ERROR
        assert (
            res_ja.answer
            == "AIプロバイダーが一時的に速度制限されています。しばらく待ってからもう一度お試しください。"
        )


def test_query_service_normalizes_insufficient_information_answer() -> None:
    """QueryService should classify a canonical refusal even if formatting changes."""
    from app.models.query_result import QueryResultKind
    from app.services.query_service import QueryService

    mock_retriever = MagicMock()
    mock_retriever.retrieve.return_value = [_chunk("dummy_chunk")]

    class MockInsufficientProvider:
        def generate_answer(self, question, context, query_language):
            return '  "The uploaded documents do not contain sufficient information to answer this question."  '

    with (
        patch(
            "app.services.query_service.DocumentRetriever", return_value=mock_retriever
        ),
        patch(
            "app.services.query_service.get_llm_provider",
            return_value=MockInsufficientProvider(),
        ),
    ):

        res = QueryService.process_question("What is the objective?", "admin", "en")
        assert res.kind == QueryResultKind.INSUFFICIENT_INFORMATION
        assert (
            res.answer
            == "The uploaded documents do not contain sufficient information to answer this question."
        )
