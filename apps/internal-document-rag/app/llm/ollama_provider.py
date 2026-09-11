import time

import requests

from app.llm.base_provider import BaseLLMProvider
from app.llm.exceptions import InvalidQueryError, LLMProviderError, ProviderTimeoutError
from app.llm.prompt_builder import PromptBuilder
from app.utils.logger import get_shared_logger

logger = get_shared_logger(__name__)


class OllamaProvider(BaseLLMProvider):
    """LLM Provider implementation for local Ollama models."""

    def __init__(self, base_url: str, model_name: str, timeout_seconds: float = 30.0):
        if not base_url:
            raise ValueError("Ollama base URL is required for OllamaProvider.")

        self._base_url = base_url.rstrip("/")
        self._model_name = model_name
        self.timeout_seconds = timeout_seconds

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate_answer(
        self, question: str, context: str, query_language: str = "en"
    ) -> str:
        if not question or not question.strip():
            raise InvalidQueryError("Question must be a non-empty string.")

        prompt = PromptBuilder.build_rag_prompt(
            question, context, query_language=query_language
        )

        import logging

        logging.getLogger(__name__).info(
            f"Generating answer via {self.provider_name} "
            f"(model: {self.model_name}, context_length: {len(context)})"
        )

        start_time = time.time()
        max_attempts = 3

        for attempt in range(1, max_attempts + 1):
            try:
                response = requests.post(
                    f"{self._base_url}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.2,
                            "num_predict": 512,
                            "top_p": 0.9,
                            "repeat_penalty": 1.1,
                            "num_ctx": 8192,
                        },
                    },
                    timeout=self.timeout_seconds,
                )
                if not response.ok:
                    logger.error(
                        f"Ollama HTTP {response.status_code} Error Detail: {response.text}"
                    )
                response.raise_for_status()
                data = response.json()
                answer = (data.get("response") or "").strip()
                if answer:
                    duration = time.time() - start_time
                    logger.info(
                        f"{self.provider_name} generation succeeded in {duration:.2f}s (response_length: {len(answer)})"
                    )
                    return answer
            except requests.exceptions.Timeout as exc:
                duration = time.time() - start_time
                logger.error(
                    f"Ollama API timeout after {duration:.2f}s: {exc}"
                )
                raise ProviderTimeoutError(
                    "Ollama answer generation timed out."
                ) from exc
            except Exception as exc:
                duration = time.time() - start_time
                logger.error(
                    f"Ollama API failure (attempt {attempt}/{max_attempts}) after {duration:.2f}s: {exc}"
                )
                if attempt < max_attempts and isinstance(
                    exc, (ConnectionError, requests.exceptions.RequestException)
                ):
                    time.sleep(2**attempt)
                    continue
                raise LLMProviderError(f"Ollama API request failed: {exc}") from exc

        raise LLMProviderError("Ollama returned an empty answer.")

    def check_health(self) -> bool:
        """Check if local Ollama server is reachable and active with installed models."""
        try:
            response = requests.get(self._base_url, timeout=3.0)
            if response.status_code != 200:
                return False
            tags_resp = requests.get(f"{self._base_url}/api/tags", timeout=3.0)
            if tags_resp.status_code == 200:
                models = tags_resp.json().get("models", [])
                return len(models) > 0
            return True
        except Exception:
            return False
