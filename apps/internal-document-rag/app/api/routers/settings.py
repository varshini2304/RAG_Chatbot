from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.schemas.base import ResponseModel
from app.api.schemas.settings import SettingsUpdateSchema, SystemSettingsSchema
from app.api.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["Settings"])


def get_settings_service() -> SettingsService:
    return SettingsService()


@router.get("", response_model=ResponseModel[SystemSettingsSchema])
def get_system_settings(
    service: SettingsService = Depends(get_settings_service),
) -> ResponseModel[SystemSettingsSchema]:
    """Retrieve platform settings."""
    settings_data = service.get_settings()
    return ResponseModel(
        success=True,
        message="System settings retrieved successfully",
        data=settings_data,
    )


@router.put("", response_model=ResponseModel[SystemSettingsSchema])
def update_system_settings(
    payload: SettingsUpdateSchema,
    service: SettingsService = Depends(get_settings_service),
) -> ResponseModel[SystemSettingsSchema]:
    """Update platform settings."""
    updated_data = service.update_settings(payload)
    return ResponseModel(
        success=True,
        message="System settings updated successfully",
        data=updated_data,
    )
