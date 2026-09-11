from __future__ import annotations

from app.api.repositories.system_repository import SystemRepository
from app.api.schemas.settings import SettingsUpdateSchema, SystemSettingsSchema


class SettingsService:
    """Service handling platform settings retrieval and updates."""

    def __init__(self) -> None:
        self.repo = SystemRepository()

    def get_settings(self) -> SystemSettingsSchema:
        """Fetch system configuration settings."""
        cfg = self.repo.get_system_config()
        return SystemSettingsSchema(**cfg)

    def update_settings(
        self, update_payload: SettingsUpdateSchema
    ) -> SystemSettingsSchema:
        """Update system configuration settings."""
        # For immutable dataclass settings, return updated view
        cfg = self.repo.get_system_config()
        if update_payload.primary_provider:
            cfg["primary_provider"] = update_payload.primary_provider
        if update_payload.secondary_provider:
            cfg["secondary_provider"] = update_payload.secondary_provider
        if update_payload.tertiary_provider:
            cfg["tertiary_provider"] = update_payload.tertiary_provider
        if update_payload.chunk_size:
            cfg["chunk_size"] = update_payload.chunk_size
        if update_payload.chunk_overlap:
            cfg["chunk_overlap"] = update_payload.chunk_overlap
        if update_payload.retrieval_top_k:
            cfg["retrieval_top_k"] = update_payload.retrieval_top_k

        return SystemSettingsSchema(**cfg)
