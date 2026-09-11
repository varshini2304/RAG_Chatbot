from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.schemas.base import ResponseModel
from app.api.schemas.monitoring import AlertItem, ErrorEvent, LogEntry, MonitoringData
from app.api.services.monitoring_service import MonitoringService

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


def get_monitoring_service() -> MonitoringService:
    return MonitoringService()


@router.get("", response_model=ResponseModel[MonitoringData])
def get_monitoring_data(
    service: MonitoringService = Depends(get_monitoring_service),
) -> ResponseModel[MonitoringData]:
    """Retrieve full monitoring diagnostic data."""
    data = service.get_monitoring_data()
    return ResponseModel(
        success=True,
        message="Monitoring diagnostic data retrieved successfully",
        data=data,
    )


@router.get("/system", response_model=ResponseModel[dict[str, float]])
def get_system_monitoring(
    service: MonitoringService = Depends(get_monitoring_service),
) -> ResponseModel[dict[str, float]]:
    """Retrieve hardware CPU, Memory, Disk gauges."""
    stats = service.system_repo.get_hardware_stats()
    return ResponseModel(
        success=True,
        message="System gauges retrieved successfully",
        data=stats,
    )


@router.get("/logs", response_model=ResponseModel[list[LogEntry]])
def get_system_logs(
    level: str | None = Query(
        None, description="Filter logs by level: INFO | WARN | ERROR | DEBUG"
    ),
    module: str | None = Query(None, description="Filter logs by module name"),
    search: str | None = Query(
        None, description="Search query string inside message or module"
    ),
    limit: int = Query(100, ge=1, le=1000, description="Max log entries to return"),
    service: MonitoringService = Depends(get_monitoring_service),
) -> ResponseModel[list[LogEntry]]:
    """Retrieve filtered runtime system logs."""
    logs = service.get_filtered_logs(
        level=level, module=module, search=search, limit=limit
    )
    return ResponseModel(
        success=True,
        message="System logs retrieved successfully",
        data=logs,
    )


@router.get("/errors", response_model=ResponseModel[list[ErrorEvent]])
def get_system_errors(
    service: MonitoringService = Depends(get_monitoring_service),
) -> ResponseModel[list[ErrorEvent]]:
    """Retrieve error events."""
    data = service.get_monitoring_data().errors
    return ResponseModel(
        success=True,
        message="System error events retrieved successfully",
        data=data,
    )


@router.get("/warnings", response_model=ResponseModel[list[dict[str, Any]]])
def get_system_warnings(
    service: MonitoringService = Depends(get_monitoring_service),
) -> ResponseModel[list[dict[str, Any]]]:
    """Retrieve warning log events."""
    warnings = service.get_warnings()
    return ResponseModel(
        success=True,
        message="System warnings retrieved successfully",
        data=warnings,
    )


@router.get("/alerts", response_model=ResponseModel[list[AlertItem]])
def get_system_alerts(
    service: MonitoringService = Depends(get_monitoring_service),
) -> ResponseModel[list[AlertItem]]:
    """Retrieve alert triggers."""
    data = service.get_monitoring_data().alerts
    return ResponseModel(
        success=True,
        message="System alerts retrieved successfully",
        data=data,
    )
