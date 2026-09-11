from __future__ import annotations

from app.api.repositories.provider_repository import ProviderRepository
from app.api.schemas.providers import ProviderInfo, ProvidersSummary


class ProviderService:
    """Service handling LLM provider operations and state queries."""

    def __init__(self) -> None:
        self.repo = ProviderRepository()

    def get_providers_summary(self) -> ProvidersSummary:
        """Compile active provider and provider list summary."""
        prov_info = self.repo.get_current_provider_info()
        all_provs = self.repo.get_all_providers_status()

        providers = [ProviderInfo(**p) for p in all_provs]

        return ProvidersSummary(
            current_provider=prov_info["active_provider"],
            providers=providers,
        )
