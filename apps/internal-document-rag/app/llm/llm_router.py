import logging
import time
from typing import Any

from app.config import settings
from app.llm.base_provider import BaseLLMProvider
from app.llm.exceptions import ConfigurationError, LLMProviderError
from app.llm.gemini_provider import GeminiProvider
from app.llm.groq_provider import GroqProvider
from app.llm.ollama_provider import OllamaProvider
from app.utils.logger import get_shared_logger

logger = get_shared_logger(__name__)


class LLMRouter(BaseLLMProvider):


    def __init__(self):
        # Lazy provider instantiations
        self._groq_provider = None
        self._gemini_provider = None
        self._ollama_provider = None

        # Circuit breaker state: provider -> {failure_count, last_failed_time}
        self._circuit_states: dict[str, dict[str, Any]] = {
            "groq": {"failure_count": 0, "last_failed_time": 0.0},
            "gemini": {"failure_count": 0, "last_failed_time": 0.0},
            "ollama": {"failure_count": 0, "last_failed_time": 0.0},
        }

        # Fallback values for non-streamlit contexts (like unit tests)
        self._local_current_provider = settings.primary_provider.capitalize()
        self._local_current_model = self._get_provider_model_name(
            settings.primary_provider
        )
        self._local_fallback_active = False
        self._local_offline_mode = False
        self._local_active_state_initialized = False

    @staticmethod
    def _normalize_provider_name(provider_name: str) -> str:
        normalized = provider_name.strip().lower()
        if normalized == "grok":
            return "groq"
        return normalized

    def _get_provider_model_name(self, provider_name: str) -> str:
        provider_name = self._normalize_provider_name(provider_name)
        if provider_name == "groq":
            return settings.groq_model_name
        elif provider_name == "gemini":
            return settings.gemini_model_name
        elif provider_name == "ollama":
            return settings.ollama_model
        return ""

    def _get_provider_timeout(self, provider_name: str) -> float:
        provider_name = self._normalize_provider_name(provider_name)
        if provider_name == "groq":
            return settings.groq_timeout
        elif provider_name == "gemini":
            return settings.gemini_timeout
        elif provider_name == "ollama":
            return settings.ollama_timeout
        return 30.0

    def _set_active_state(
        self,
        provider_name: str,
        model_name: str,
        fallback_active: bool,
        offline_mode: bool,
    ):
        # Normalize provider display name (e.g. Groq, Gemini, Ollama)
        disp_name = provider_name.capitalize()
        self._local_current_provider = disp_name
        self._local_current_model = model_name
        self._local_fallback_active = fallback_active
        self._local_offline_mode = offline_mode
        self._local_active_state_initialized = True

    def get_active_state_snapshot(self) -> dict[str, Any]:
        """Return the router's current active provider state for non-UI consumers such as the admin API."""
        return {
            "provider": self._local_current_provider,
            "model": self._local_current_model,
            "fallback_active": self._local_fallback_active,
            "offline_mode": self._local_offline_mode,
            "initialized": self._local_active_state_initialized,
        }

    @property
    def provider_name(self) -> str:
        return self._local_current_provider

    @property
    def model_name(self) -> str:
        return self._local_current_model

    def is_offline_mode_active(self) -> bool:
        if self._local_active_state_initialized:
            return bool(self._local_offline_mode)
        return settings.offline_mode

    def set_offline_mode(self, active: bool):
        """Authoritatively set offline mode state for the router instance."""
        target_provider = "Ollama" if active else settings.primary_provider.capitalize()
        model_name = self._get_provider_model_name(target_provider)
        self._set_active_state(target_provider, model_name, False, active)

    def _get_provider(self, name: str) -> BaseLLMProvider:
        name = self._normalize_provider_name(name)
        if self.is_offline_mode_active() and name in ("groq", "gemini"):
            raise LLMProviderError(
                f"🔒 Offline Mode Active: Refusing to invoke external provider '{name}'."
            )
        timeout = self._get_provider_timeout(name)
        if name == "groq":
            if self._groq_provider is None:
                if not settings.groq_api_key:
                    raise ConfigurationError("GROQ_API_KEY is not set.")
                self._groq_provider = GroqProvider(
                    api_key=settings.groq_api_key,
                    model_name=settings.groq_model_name,
                    timeout_seconds=timeout,
                )
            return self._groq_provider
        elif name == "gemini":
            if self._gemini_provider is None:
                if not settings.google_api_key:
                    raise ConfigurationError("GOOGLE_API_KEY is not set.")
                self._gemini_provider = GeminiProvider(
                    api_key=settings.google_api_key,
                    model_name=settings.gemini_model_name,
                    timeout_seconds=timeout,
                )
            return self._gemini_provider
        elif name == "ollama":
            if self._ollama_provider is None:
                self._ollama_provider = OllamaProvider(
                    base_url=settings.ollama_url,
                    model_name=settings.ollama_model,
                    timeout_seconds=timeout,
                )
            return self._ollama_provider
        else:
            raise ConfigurationError(f"Unsupported LLM provider requested: {name}")

    def is_circuit_open(self, provider_name: str) -> bool:
        """Determine if the circuit breaker is OPEN (tripped) for a provider."""
        state = self._circuit_states.get(self._normalize_provider_name(provider_name))
        if not state:
            return False

        # If failures exceeded the threshold, check cooldown
        if state["failure_count"] >= settings.circuit_breaker_threshold:
            elapsed = time.time() - state["last_failed_time"]
            if elapsed < settings.circuit_breaker_cooldown:
                return True
            else:
                # Cooldown period expired, transition to HALF-OPEN (permit a trial)
                logger.info(
                    f"Circuit breaker for {provider_name} transitioned from OPEN to HALF-OPEN."
                )
                return False
        return False

    def record_success(self, provider_name: str):
        """Record a successful execution, closing the circuit breaker."""
        state = self._circuit_states.get(self._normalize_provider_name(provider_name))
        if state:
            state["failure_count"] = 0
            state["last_failed_time"] = 0.0

    def record_failure(self, provider_name: str):
        """Record a failure, potentially tripping the circuit breaker."""
        state = self._circuit_states.get(self._normalize_provider_name(provider_name))
        if state:
            state["failure_count"] += 1
            state["last_failed_time"] = time.time()
            if state["failure_count"] >= settings.circuit_breaker_threshold:
                logger.warning(
                    f"Circuit breaker for {provider_name} TRIPPED to OPEN due to "
                    f"{state['failure_count']} consecutive failures."
                )

    def generate_answer(
        self, question: str, context: str, query_language: str = "en"
    ) -> str:
        # Construct current priority list of providers
        if self.is_offline_mode_active():
            providers_order = ["ollama"]
        else:
            providers_order = [
                settings.primary_provider,
                settings.secondary_provider,
                settings.tertiary_provider,
            ]

        sys_logger = logging.getLogger(__name__)
        last_exc = None

        for idx, provider_name in enumerate(providers_order):
            if not provider_name:
                continue

            provider_name = self._normalize_provider_name(provider_name)
            model_name = self._get_provider_model_name(provider_name)

            # Check if circuit is open
            if self.is_circuit_open(provider_name):
                sys_logger.warning(
                    f"Provider {provider_name.capitalize()} skipped (Circuit Breaker OPEN). Attempting failover..."
                )
                continue

            start_time = time.time()
            try:
                provider = self._get_provider(provider_name)
                # Attempt generation
                answer = provider.generate_answer(question, context, query_language)

                # Success! Record and reset circuit breaker
                self.record_success(provider_name)

                # Update status
                fallback_active = idx > 0 and provider_name != "ollama"
                offline_mode = self.is_offline_mode_active()
                self._set_active_state(
                    provider_name, model_name, fallback_active, offline_mode
                )

                duration = time.time() - start_time
                sys_logger.info(
                    f"Response successfully generated using {provider_name.capitalize()} ({model_name}) in {duration:.2f}s."
                )
                return answer

            except Exception as exc:
                last_exc = exc
                self.record_failure(provider_name)
                sys_logger.warning(
                    f"Provider {provider_name.capitalize()} failed ({exc}). Failing over to next available provider..."
                )
                continue

        # If all providers fail:
        logger.error(f"All configured providers failed. Final exception: {last_exc}")
        self._set_active_state("None", "None", False, self.is_offline_mode_active())
        if self.is_offline_mode_active():
            raise LLMProviderError(
                "🔒 Offline Mode Active: External providers (Gemini/Groq) are disabled. "
                "Local Ollama service is unavailable or failed."
            )
        raise LLMProviderError(
            "⚠️ Chatbot is currently unavailable. Please try again later."
        )

    def select_highest_priority_provider(self) -> str:
        if self.is_offline_mode_active():
            providers_order = ["ollama"]
        else:
            providers_order = [
                settings.primary_provider,
                settings.secondary_provider,
                settings.tertiary_provider,
            ]

        sys_logger = logging.getLogger(__name__)

        for idx, provider in enumerate(providers_order):
            if not provider:
                continue
            name = self._normalize_provider_name(provider)
            try:
                prov_inst = self._get_provider(name)
                check_health_fn = getattr(prov_inst, "check_health", None)
                if check_health_fn and check_health_fn():
                    model_name = self._get_provider_model_name(name)
                    fallback_active = (
                        name != self._normalize_provider_name(settings.primary_provider)
                        and name != "ollama"
                    )
                    offline_mode = self.is_offline_mode_active()
                    self._set_active_state(
                        name, model_name, fallback_active, offline_mode
                    )

                    if idx > 0:
                        sys_logger.warning(
                            f"LLM Failover Active: Provider '{providers_order[0].capitalize()}' failed health check. Switched active provider to '{name.capitalize()}' ({model_name})."
                        )
                    sys_logger.info(
                        f"Active LLM Provider is {name.capitalize()} (model: {model_name}) - status: Online & Ready."
                    )
                    return name
                else:
                    sys_logger.warning(
                        f"Provider {name.capitalize()} failed health check. Failing over to next available LLM..."
                    )
            except Exception as exc:
                sys_logger.warning(
                    f"Provider {name.capitalize()} health check error ({exc}). Failing over to next LLM..."
                )
                continue

        sys_logger.error(
            "All configured LLM providers failed health checks. Chatbot is unavailable."
        )
        self._set_active_state("None", "None", False, False)
        return "None"

    def check_health_all(self) -> dict[str, str]:
        """
        Determine health based on circuit breaker states.
        If circuit is OPEN, status is 'Unavailable', else 'Available'.
        """
        results = {}
        for p in ["groq", "gemini", "ollama"]:
            # If circuit is open, it is Unavailable
            if self.is_circuit_open(p):
                results[p] = "Unavailable"
            else:
                results[p] = "Available"
        return results
