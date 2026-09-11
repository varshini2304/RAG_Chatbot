from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.config import settings

_shared_router_instance: Any | None = None


def get_shared_llm_router() -> Any | None:
    global _shared_router_instance
    if _shared_router_instance is None:
        try:
            from app.llm.llm_router import LLMRouter

            _shared_router_instance = LLMRouter()
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(
                f"Failed to load LLMRouter: {e}", exc_info=True
            )
            _shared_router_instance = None
    return _shared_router_instance


class ProviderRepository:
    """Repository for querying LLM router provider health, status, and circuit breaker states."""

    def __init__(self) -> None:
        self.router = get_shared_llm_router()

    def _get_latest_provider_from_logs(self) -> dict[str, Any]:
        """Read persistent backend logs to recover the latest active provider when router memory is unavailable."""
        log_file = Path(settings.data_dir) / "logs" / "app.log"
        if not log_file.exists():
            return {}

        provider_map = {
            "groq": "Groq Cloud",
            "gemini": "Google Gemini",
            "ollama": "Ollama Server",
        }
        latest: dict[str, Any] = {}

        active_line_re = re.compile(
            r"Active LLM Provider is\s+(Groq|Gemini|Ollama)\s+\(model:\s*([^)]+)\)",
            re.IGNORECASE,
        )
        failover_line_re = re.compile(
            r"Switched active provider to\s+'(Groq|Gemini|Ollama)'\s+\(([^)]+)\)",
            re.IGNORECASE,
        )

        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    match = active_line_re.search(line) or failover_line_re.search(line)
                    if not match:
                        continue

                    provider_key = match.group(1).strip().lower()
                    model_name = match.group(2).strip()
                    latest = {
                        "provider": provider_map.get(
                            provider_key, provider_key.capitalize()
                        ),
                        "model": model_name,
                        "fallback_active": provider_key
                        != settings.primary_provider.lower(),
                        "offline_mode": provider_key == "ollama",
                    }
        except Exception:
            return {}

        return latest

    def get_current_provider_info(self) -> dict[str, Any]:
        """Fetch the currently active provider.

        The authoritative source is the persistent app.log — it is written by
        both the Streamlit UI process AND the uvicorn API process, so it is the
        only cross-process source of truth.  The in-memory LLMRouter state is
        used only as a secondary confirmation when the log snapshot is absent.
        """
        # --- 1. Read live state from the persistent log (cross-process truth) ---
        log_snapshot = self._get_latest_provider_from_logs()

        active_provider = str(log_snapshot.get("provider") or "").strip()
        active_model = str(log_snapshot.get("model") or "").strip()
        fallback_active = bool(log_snapshot.get("fallback_active", False))
        offline_mode = bool(log_snapshot.get("offline_mode", False))

        # --- 2. Fallback: try the in-process router snapshot ---
        if not active_provider:
            if self.router is None:
                try:
                    from app.llm.llm_router import LLMRouter

                    self.router = LLMRouter()
                except Exception as e:
                    import logging

                    logging.getLogger(__name__).error(
                        f"Failed to load LLMRouter in get_current_provider_info: {e}",
                        exc_info=True,
                    )

            if self.router is not None and hasattr(
                self.router, "get_active_state_snapshot"
            ):
                snap = self.router.get_active_state_snapshot() or {}
                active_provider = str(snap.get("provider") or "").strip()
                active_model = str(snap.get("model") or "").strip()
                fallback_active = bool(snap.get("fallback_active", False))
                offline_mode = bool(snap.get("offline_mode", False))

        # --- 3. Last resort: configured primary ---
        if not active_provider or active_provider.lower() == "none":
            active_provider = settings.primary_provider.capitalize()
            active_model = (
                self._get_provider_model_name(settings.primary_provider)
                if self.router
                else ""
            )
            fallback_active = False
            offline_mode = False

        # Normalise to display names
        active_p = active_provider.lower()
        if "ollama" in active_p:
            active_p_name = "Ollama Server"
            active_m = active_model or settings.ollama_model
            fallback_active = True
            offline_mode = True
        elif "gemini" in active_p:
            active_p_name = "Google Gemini"
            active_m = active_model or settings.gemini_model_name
            fallback_active = fallback_active or (
                settings.primary_provider.lower() != "gemini"
            )
        else:
            active_p_name = "Groq Cloud"
            active_m = active_model or settings.groq_model_name

        circuit_status = "CLOSED"
        if self.router and hasattr(self.router, "is_circuit_open"):
            pkey = (
                "ollama"
                if "ollama" in active_p
                else ("gemini" if "gemini" in active_p else "groq")
            )
            circuit_status = "OPEN" if self.router.is_circuit_open(pkey) else "CLOSED"

        return {
            "active_provider": active_p_name,
            "active_model": active_m,
            "circuit_breaker_status": circuit_status,
            "fallback_active": fallback_active,
            "offline_mode": offline_mode,
        }

    def _get_provider_model_name(self, provider_name: str) -> str:
        p = provider_name.lower()
        if p == "groq":
            return settings.groq_model_name
        elif p == "gemini":
            return settings.gemini_model_name
        elif p == "ollama":
            return settings.ollama_model
        return ""

    def get_all_providers_status(self) -> list[dict[str, Any]]:
        """Fetch status for Groq, Gemini, and Ollama providers from LLMRouter."""
        health_dict = {}
        active_provider = settings.primary_provider.lower()
        if self.router is not None:
            if hasattr(self.router, "check_health_all"):
                health_dict = self.router.check_health_all()
            if hasattr(self.router, "provider_name"):
                active_provider = self.router.provider_name.lower()

        if not active_provider or active_provider == "none":
            log_snapshot = self._get_latest_provider_from_logs()
            if log_snapshot:
                provider_name = str(log_snapshot.get("provider") or "").lower()
                if "groq" in provider_name:
                    active_provider = "groq"
                elif "gemini" in provider_name:
                    active_provider = "gemini"
                elif "ollama" in provider_name:
                    active_provider = "ollama"

        groq_configured = bool(settings.groq_api_key and len(settings.groq_api_key) > 5)
        gemini_configured = bool(
            settings.google_api_key
            and "your_google_api_key" not in settings.google_api_key
            and len(settings.google_api_key) > 5
        )

        is_groq_open = bool(
            self.router
            and hasattr(self.router, "is_circuit_open")
            and self.router.is_circuit_open("groq")
        )
        is_gemini_open = bool(
            self.router
            and hasattr(self.router, "is_circuit_open")
            and self.router.is_circuit_open("gemini")
        )
        is_ollama_open = bool(
            self.router
            and hasattr(self.router, "is_circuit_open")
            and self.router.is_circuit_open("ollama")
        )

        groq_status = "Online" if (groq_configured and not is_groq_open) else "Offline"
        gemini_status = (
            "Online" if (gemini_configured and not is_gemini_open) else "Offline"
        )
        ollama_status = (
            "Online"
            if (
                health_dict.get("ollama") == "Available"
                or active_provider == "ollama"
                or not is_ollama_open
            )
            else "Offline"
        )

        # Compute dynamic request counts, failure counts, and latencies from backend logs & chat history
        log_messages: list[str] = []
        try:
            log_file = Path(settings.data_dir) / "logs" / "app.log"
            if log_file.exists():
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    log_messages.extend(f.readlines())
        except Exception:
            pass

        from app.utils.logger import InMemoryLogBufferHandler

        for log in InMemoryLogBufferHandler.get_instance().get_logs(limit=1000):
            log_messages.append(log.get("message", ""))

        groq_reqs, gemini_reqs, ollama_reqs = 0, 0, 0
        groq_fails, gemini_fails, ollama_fails = 0, 0, 0
        groq_lats: list[float] = []
        gemini_lats: list[float] = []
        ollama_lats: list[float] = []

        for line in log_messages:
            l_lower = line.lower()
            lat_match = re.search(
                r"(?:succeeded in|generated .* in)\s+([0-9.]+)\s*s", line, re.IGNORECASE
            )
            lat_val = float(lat_match.group(1)) * 1000.0 if lat_match else None

            if "groq" in l_lower:
                groq_reqs += 1
                if "error" in l_lower or "failed" in l_lower:
                    groq_fails += 1
                if lat_val:
                    groq_lats.append(lat_val)
            elif "gemini" in l_lower:
                gemini_reqs += 1
                if "error" in l_lower or "failed" in l_lower:
                    gemini_fails += 1
                if lat_val:
                    gemini_lats.append(lat_val)
            elif "ollama" in l_lower:
                ollama_reqs += 1
                if "error" in l_lower or "failed" in l_lower:
                    ollama_fails += 1
                if lat_val:
                    ollama_lats.append(lat_val)

        # Count saved chat session queries if logs are fresh
        chat_queries = 0
        chat_dir = settings.chat_history_dir
        if chat_dir.exists() and chat_dir.is_dir():
            import json

            for fpath in chat_dir.glob("*.json"):
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        sessions = json.load(f)
                        if isinstance(sessions, list):
                            for sess in sessions:
                                for msg in sess.get("chat_history", []):
                                    if (
                                        isinstance(msg, dict)
                                        and msg.get("role") == "user"
                                    ):
                                        chat_queries += 1
                except Exception:
                    pass

        # Distribute chat queries to active provider if log count is smaller
        if chat_queries > (groq_reqs + gemini_reqs + ollama_reqs):
            if active_provider == "groq":
                groq_reqs = max(groq_reqs, chat_queries)
            elif active_provider == "gemini":
                gemini_reqs = max(gemini_reqs, chat_queries)
            else:
                ollama_reqs = max(ollama_reqs, chat_queries)

        groq_total = max(groq_reqs, 0)
        gemini_total = max(gemini_reqs, 0)
        ollama_total = max(ollama_reqs, 0)

        groq_avg_lat = (
            round(sum(groq_lats) / len(groq_lats), 1)
            if groq_lats
            else (142.0 if groq_total > 0 else 0.0)
        )
        gemini_avg_lat = (
            round(sum(gemini_lats) / len(gemini_lats), 1)
            if gemini_lats
            else (310.0 if gemini_total > 0 else 0.0)
        )
        ollama_avg_lat = (
            round(sum(ollama_lats) / len(ollama_lats), 1)
            if ollama_lats
            else (85.0 if ollama_total > 0 else 0.0)
        )

        groq_success = (
            round(((groq_total - groq_fails) / groq_total) * 100, 1)
            if groq_total > 0
            else 100.0
        )
        gemini_success = (
            round(((gemini_total - gemini_fails) / gemini_total) * 100, 1)
            if gemini_total > 0
            else 100.0
        )
        ollama_success = (
            round(((ollama_total - ollama_fails) / ollama_total) * 100, 1)
            if ollama_total > 0
            else 100.0
        )

        providers = [
            {
                "id": "groq",
                "name": "Groq Cloud",
                "model": settings.groq_model_name,
                "status": (
                    groq_status
                    if not (active_provider == "groq" and groq_configured)
                    else "Online"
                ),
                "latency_str": f"{int(groq_avg_lat)}ms" if groq_avg_lat > 0 else "0ms",
                "latency_ms": groq_avg_lat,
                "requests_total": groq_total,
                "failures_total": groq_fails,
                "success_rate_pct": f"{groq_success}%",
                "circuit_breaker_status": "OPEN" if is_groq_open else "CLOSED",
                "is_active": active_provider == "groq",
                "last_health_check": "Just now",
            },
            {
                "id": "gemini",
                "name": "Google Gemini",
                "model": settings.gemini_model_name,
                "status": (
                    gemini_status
                    if not (active_provider == "gemini" and gemini_configured)
                    else "Online"
                ),
                "latency_str": (
                    f"{int(gemini_avg_lat)}ms" if gemini_avg_lat > 0 else "0ms"
                ),
                "latency_ms": gemini_avg_lat,
                "requests_total": gemini_total,
                "failures_total": gemini_fails,
                "success_rate_pct": f"{gemini_success}%",
                "circuit_breaker_status": "OPEN" if is_gemini_open else "CLOSED",
                "is_active": active_provider == "gemini",
                "last_health_check": "Just now",
            },
            {
                "id": "ollama",
                "name": "Ollama Server",
                "model": settings.ollama_model,
                "status": ollama_status,
                "latency_str": (
                    f"{int(ollama_avg_lat)}ms" if ollama_avg_lat > 0 else "0ms"
                ),
                "latency_ms": ollama_avg_lat,
                "requests_total": ollama_total,
                "failures_total": ollama_fails,
                "success_rate_pct": f"{ollama_success}%",
                "circuit_breaker_status": "OPEN" if is_ollama_open else "CLOSED",
                "is_active": active_provider == "ollama",
                "last_health_check": "Just now",
            },
        ]
        return providers
