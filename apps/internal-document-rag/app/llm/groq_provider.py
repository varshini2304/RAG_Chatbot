import logging
import time

try:
    from langchain_core.messages import HumanMessage
    from langchain_groq import ChatGroq
    from pydantic import SecretStr

    _GROQ_AVAILABLE = True
    _GROQ_IMPORT_ERROR = None
except Exception as err:
    _GROQ_AVAILABLE = False
    _GROQ_IMPORT_ERROR = str(err)
    ChatGroq = None
    HumanMessage = None
    SecretStr = None


from app.llm.base_provider import BaseLLMProvider
from app.llm.exceptions import (
    GroqProviderError,
    InvalidQueryError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)
from app.llm.prompt_builder import PromptBuilder
from app.utils.logger import get_shared_logger

logger = get_shared_logger(__name__)


class GroqProvider(BaseLLMProvider):
    """LLM Provider implementation for Groq."""

    def __init__(self, api_key: str, model_name: str, timeout_seconds: float = 30.0):
        if not _GROQ_AVAILABLE or ChatGroq is None or SecretStr is None:
            raise GroqProviderError(
                f"Groq SDK is unavailable due to environment or system policy restriction: {_GROQ_IMPORT_ERROR}"
            )
        if not api_key:
            raise ValueError("GROQ_API_KEY is required for GroqProvider.")

        self._api_key = api_key
        self._model_name = model_name
        self.timeout_seconds = timeout_seconds

        assert ChatGroq is not None and SecretStr is not None
        self._client = ChatGroq(
            api_key=SecretStr(self._api_key),
            model=self._model_name,
            timeout=self.timeout_seconds,
        )

    @property
    def provider_name(self) -> str:
        return "groq"

    @property
    def model_name(self) -> str:
        return self._model_name

    def check_health(self) -> bool:
        """Check connectivity and credentials validity for Groq API."""
        if (
            not self._api_key
            or "your_groq_api_key" in self._api_key
            or not self._api_key.strip()
        ):
            return False
        import requests

        try:
            response = requests.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {self._api_key.strip()}"},
                timeout=5.0,
            )
            return response.status_code == 200
        except Exception:
            return False

    def generate_answer(
        self, question: str, context: str, query_language: str = "en"
    ) -> str:
        if not _GROQ_AVAILABLE or HumanMessage is None or self._client is None:
            raise GroqProviderError(
                f"Groq provider SDK is unavailable: {_GROQ_IMPORT_ERROR}"
            )
        if not question or not question.strip():
            raise InvalidQueryError("Question must be a non-empty string.")

        prompt = PromptBuilder.build_rag_prompt(
            question, context, query_language=query_language
        )

        logger.info(
            f"Generating answer via {self.provider_name} "
            f"(model: {self.model_name}, context_length: {len(context)})"
        )

        start_time = time.time()
        max_attempts = 3

        for attempt in range(1, max_attempts + 1):
            try:
                message = HumanMessage(content=prompt)
                response = self._client.invoke([message])
                answer = str(response.content).strip() if response.content else ""
                if not answer:
                    logger.error("Groq answer generation failed: empty response")
                    raise GroqProviderError("Groq returned an empty answer.")

                duration = time.time() - start_time
                logging.getLogger(__name__).info(
                    f"{self.provider_name} generation succeeded in {duration:.2f}s (response_length: {len(answer)})"
                )
                return answer
            except Exception as exc:
                if isinstance(exc, GroqProviderError):
                    raise
                duration = time.time() - start_time
                logger.error(
                    f"Groq API failure (attempt {attempt}/{max_attempts}) after {duration:.2f}s: {exc}"
                )

                exc_name = type(exc).__name__.lower()
                if "timeout" in exc_name:
                    err = ProviderTimeoutError("Groq answer generation timed out.")
                elif self._is_rate_limit_error(exc):
                    err = ProviderRateLimitError("Groq API rate limit exceeded.")
                elif isinstance(exc, ConnectionError) or "connection" in exc_name:
                    err = ProviderTimeoutError("Groq API connection failed.")
                else:
                    err = GroqProviderError(f"Groq API request failed: {exc}")

                if attempt < max_attempts and isinstance(
                    err, (ProviderTimeoutError, ProviderRateLimitError)
                ):
                    time.sleep(2**attempt)
                    continue
                raise err from exc
        return ""

    @staticmethod
    def _is_rate_limit_error(exc: BaseException) -> bool:
        """Recognize rate limit (429) or quota exceeded exceptions through their chain."""
        current: BaseException | None = exc
        while current is not None:
            exc_str = str(current).lower()
            exc_name = type(current).__name__.lower()

            if hasattr(current, "status_code") and current.status_code == 429:
                return True
            if hasattr(current, "status") and current.status == 429:
                return True
            if hasattr(current, "code") and current.code == 429:
                return True

            if (
                "429" in exc_str
                or "quota exceeded" in exc_str
                or "rate_limit" in exc_str
                or "rate limit" in exc_str
                or "ratelimit" in exc_str
            ):
                return True
            if "ratelimit" in exc_name or "quota" in exc_name:
                return True

            current = current.__cause__ or current.__context__
        return False
