import logging
import time

try:
    from google import genai
    from google.genai import types

    _GENAI_AVAILABLE = bool(genai and types)
    _GENAI_IMPORT_ERROR = None
except Exception as err:
    _GENAI_AVAILABLE = False
    _GENAI_IMPORT_ERROR = str(err)
    genai = None
    types = None


from app.llm.base_provider import BaseLLMProvider
from app.llm.exceptions import (
    GeminiProviderError,
    InvalidQueryError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)
from app.llm.prompt_builder import PromptBuilder
from app.utils.logger import get_shared_logger

logger = get_shared_logger(__name__)


class GeminiProvider(BaseLLMProvider):
    """LLM Provider implementation for Google Gemini."""

    def __init__(self, api_key: str, model_name: str, timeout_seconds: float = 30.0):
        if not _GENAI_AVAILABLE or genai is None or types is None:
            raise GeminiProviderError(
                f"Google GenAI SDK is unavailable due to environment or system policy restriction: {_GENAI_IMPORT_ERROR}"
            )
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is required for GeminiProvider.")

        self._api_key = api_key
        self._model_name = model_name
        self.timeout_seconds = timeout_seconds

        assert genai is not None and types is not None
        self._client = genai.Client(
            api_key=self._api_key,
            http_options=types.HttpOptions(timeout=int(timeout_seconds * 1000)),
        )

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model_name

    def check_health(self) -> bool:
        """Check connectivity and credentials validity for Google Gemini API."""
        if (
            not self._api_key
            or "your_google_api_key" in self._api_key
            or not self._api_key.strip()
        ):
            return False
        import requests

        try:
            response = requests.get(
                f"https://generativelanguage.googleapis.com/v1beta/models?key={self._api_key}",
                timeout=2.0,
            )
            return response.status_code == 200
        except Exception:
            return False

    def generate_answer(
        self, question: str, context: str, query_language: str = "en"
    ) -> str:
        if not _GENAI_AVAILABLE or genai is None or self._client is None:
            raise GeminiProviderError(
                f"Google GenAI SDK is unavailable: {_GENAI_IMPORT_ERROR}"
            )
        if not question or not question.strip():
            raise InvalidQueryError("Question must be a non-empty string.")

        prompt = PromptBuilder.build_rag_prompt(
            question, context, query_language=query_language
        )

        logging.getLogger(__name__).info(
            f"Generating answer via {self.provider_name} "
            f"(model: {self.model_name}, context_length: {len(context)})"
        )

        start_time = time.time()
        max_attempts = 3

        for attempt in range(1, max_attempts + 1):
            try:
                response = self._client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                )
                answer = response.text.strip() if response.text else ""
                if not answer:
                    logger.error("Gemini answer generation failed: empty response")
                    raise GeminiProviderError("Gemini returned an empty answer.")

                duration = time.time() - start_time
                logging.getLogger(__name__).info(
                    f"{self.provider_name} generation succeeded in {duration:.2f}s (response_length: {len(answer)})"
                )
                return answer
            except Exception as exc:
                if isinstance(exc, GeminiProviderError):
                    raise
                duration = time.time() - start_time
                clean_msg = str(exc).split("\n")[0]
                logger.error(
                    f"Gemini API failure (attempt {attempt}/{max_attempts}) after {duration:.2f}s: {clean_msg}"
                )

                if self._is_timeout_error(exc):
                    err = ProviderTimeoutError("Gemini answer generation timed out.")
                elif self._is_rate_limit_error(exc):
                    err = ProviderRateLimitError("Gemini API rate limit exceeded.")
                elif (
                    isinstance(exc, ConnectionError)
                    or "connection" in type(exc).__name__.lower()
                ):
                    err = ProviderTimeoutError("Gemini API connection failed.")
                else:
                    err = GeminiProviderError(f"Gemini API request failed: {exc}")

                if attempt < max_attempts and isinstance(
                    err, (ProviderTimeoutError, ProviderRateLimitError)
                ):
                    time.sleep(2**attempt)
                    continue
                raise err from exc
        return ""

    @staticmethod
    def _is_timeout_error(exc: BaseException) -> bool:
        """Recognize built-in and HTTP-client timeout exceptions through their chain."""
        current: BaseException | None = exc
        while current is not None:
            if (
                isinstance(current, TimeoutError)
                or "timeout" in type(current).__name__.lower()
            ):
                return True
            current = current.__cause__ or current.__context__
        return False

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
