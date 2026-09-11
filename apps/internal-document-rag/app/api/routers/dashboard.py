from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.schemas.base import ResponseModel
from app.api.schemas.dashboard import (
    ActivityItem,
    DashboardOverviewData,
    ProviderStatusSummary,
    SystemHealthSummary,
)
from app.api.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def get_dashboard_service() -> DashboardService:
    return DashboardService()


@router.get("/overview", response_model=ResponseModel[DashboardOverviewData])
def get_dashboard_overview(
    service: DashboardService = Depends(get_dashboard_service),
) -> ResponseModel[DashboardOverviewData]:
    """Retrieve full dashboard overview metrics and system status."""
    data = service.get_overview()
    return ResponseModel(
        success=True,
        message="Dashboard overview retrieved successfully - v2",
        data=data,
    )


@router.get("/system-health", response_model=ResponseModel[SystemHealthSummary])
def get_system_health(
    service: DashboardService = Depends(get_dashboard_service),
) -> ResponseModel[SystemHealthSummary]:
    """Retrieve real-time hardware metrics and ChromaDB status."""
    data = service.get_overview().systemHealth
    return ResponseModel(
        success=True,
        message="System health metrics retrieved successfully",
        data=data,
    )


@router.get("/provider-status", response_model=ResponseModel[ProviderStatusSummary])
def get_provider_status(
    service: DashboardService = Depends(get_dashboard_service),
) -> ResponseModel[ProviderStatusSummary]:
    """Retrieve active LLM provider health and circuit breaker status."""
    data = service.get_overview().providerStatus
    return ResponseModel(
        success=True,
        message="Provider status retrieved successfully",
        data=data,
    )


@router.get("/recent-activity", response_model=ResponseModel[list[ActivityItem]])
def get_recent_activity(
    service: DashboardService = Depends(get_dashboard_service),
) -> ResponseModel[list[ActivityItem]]:
    """Retrieve recent system audit activity items."""
    data = service.get_overview().recentActivities
    return ResponseModel(
        success=True,
        message="Recent activity retrieved successfully",
        data=data,
    )
