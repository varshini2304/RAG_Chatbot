class LLMProviderError(RuntimeError):
    """Base exception for all LLM provider failures."""


class InvalidQueryError(LLMProviderError):
    """Raised when the user question is empty or invalid."""


class EmptyContextError(LLMProviderError):
    """Raised when retrieval provides no chunks for grounding."""


class ConfigurationError(LLMProviderError):
    """Raised when provider configuration is missing or invalid."""


class GeminiProviderError(LLMProviderError):
    """Raised when Gemini API fails."""


class GroqProviderError(LLMProviderError):
    """Raised when Groq API fails."""


class ProviderTimeoutError(LLMProviderError):
    """Raised when any LLM provider exceeds its configured timeout."""


class ProviderRateLimitError(LLMProviderError):
    """Raised when the AI provider is rate-limited (HTTP 429)."""
