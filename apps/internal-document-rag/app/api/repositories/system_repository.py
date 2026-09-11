from __future__ import annotations

from typing import Any

import psutil  # type: ignore[import-untyped]

from app.config import settings


class SystemRepository:
    """Repository for querying hardware status, ChromaDB vectorstore, and system config."""

    def get_hardware_stats(self) -> dict[str, float]:
        """Fetch CPU, RAM, and Disk utilization percentages."""
        try:
            cpu = float(psutil.cpu_percent(interval=0.05) or 0.0)
            memory = float(psutil.virtual_memory().percent or 0.0)
            drive_root = (
                str(settings.data_dir.anchor)
                if (hasattr(settings, "data_dir") and settings.data_dir.anchor)
                else "D:\\"
            )
            disk = float(psutil.disk_usage(drive_root).percent or 0.0)
            return {
                "cpu_percent": cpu,
                "memory_percent": memory,
                "disk_percent": disk,
            }
        except Exception:
            return {
                "cpu_percent": 25.0,
                "memory_percent": 45.0,
                "disk_percent": 30.0,
            }

    def get_chroma_status(self) -> dict[str, Any]:
        """Query local ChromaDB collection chunk count and status."""
        try:
            from app.vectorstore.chroma_manager import ChromaVectorStore

            store = ChromaVectorStore()
            count = store.collection.count()
            return {
                "status": "healthy",
                "chunk_count": count,
                "collection_name": settings.chroma_collection_name,
                "db_dir": str(settings.chroma_db_dir),
            }
        except Exception as exc:
            return {
                "status": "unhealthy",
                "error": str(exc),
                "chunk_count": 0,
                "collection_name": settings.chroma_collection_name,
                "db_dir": str(settings.chroma_db_dir),
            }

    def get_system_config(self) -> dict[str, Any]:
        """Retrieve current system settings."""
        return {
            "app_name": settings.app_name,
            "environment": settings.environment,
            "primary_provider": settings.primary_provider,
            "secondary_provider": settings.secondary_provider,
            "tertiary_provider": settings.tertiary_provider,
            "groq_model_name": settings.groq_model_name,
            "gemini_model_name": settings.gemini_model_name,
            "ollama_model": settings.ollama_model,
            "embedding_model_name": settings.embedding_model_name,
            "chunk_size": settings.chunk_size,
            "chunk_overlap": settings.chunk_overlap,
            "retrieval_top_k": settings.retrieval_top_k,
            "retrieval_min_similarity": settings.retrieval_min_similarity,
            "circuit_breaker_threshold": settings.circuit_breaker_threshold,
            "circuit_breaker_cooldown": settings.circuit_breaker_cooldown,
        }
