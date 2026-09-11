from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of the provider (e.g., 'gemini', 'groq')."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the specific model name being used."""

    @abstractmethod
    def generate_answer(
        self, question: str, context: str, query_language: str = "en"
    ) -> str:
        """
        Generate an answer to a question using the provided context.
        Must raise appropriate LLMProviderError exceptions on failure.
        """
