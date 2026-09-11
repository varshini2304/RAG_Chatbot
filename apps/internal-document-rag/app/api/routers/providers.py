from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.schemas.base import ResponseModel
from app.api.schemas.providers import ProviderInfo, ProvidersSummary
from app.api.services.provider_service import ProviderService

router = APIRouter(prefix="/providers", tags=["Providers"])


def get_provider_service() -> ProviderService:
    return ProviderService()


@router.get("", response_model=ResponseModel[ProvidersSummary])
def get_providers_summary(
    service: ProviderService = Depends(get_provider_service),
) -> ResponseModel[ProvidersSummary]:
    """Retrieve full provider summary and status list."""
    data = service.get_providers_summary()
    return ResponseModel(
        success=True,
        message="Providers summary retrieved successfully",
        data=data,
    )


@router.get("/current", response_model=ResponseModel[dict[str, str]])
def get_current_provider(
    service: ProviderService = Depends(get_provider_service),
) -> ResponseModel[dict[str, str]]:
    """Retrieve currently active LLM provider name and model."""
    prov_info = service.repo.get_current_provider_info()
    active = prov_info.get("active_provider", "Groq Cloud")
    # Map display name → raw key for frontend
    key_map = {
        "Groq Cloud": "groq",
        "Google Gemini": "gemini",
        "Ollama Server": "ollama",
    }
    return ResponseModel(
        success=True,
        message="Current provider retrieved successfully",
        data={
            "current_provider": key_map.get(active, "groq"),
            "active_provider": active,
            "active_model": prov_info.get("active_model", ""),
            "fallback_active": str(prov_info.get("fallback_active", False)).lower(),
            "offline_mode": str(prov_info.get("offline_mode", False)).lower(),
        },
    )


@router.get("/status", response_model=ResponseModel[list[ProviderInfo]])
def get_providers_status(
    service: ProviderService = Depends(get_provider_service),
) -> ResponseModel[list[ProviderInfo]]:
    """Retrieve health and circuit status for Groq, Gemini, and Ollama."""
    providers = service.get_providers_summary().providers
    return ResponseModel(
        success=True,
        message="Provider health statuses retrieved successfully",
        data=providers,
    )
