from __future__ import annotations

from typing import Any

from app.api.repositories.analytics_repository import AnalyticsRepository
from app.api.repositories.system_repository import SystemRepository
from app.api.schemas.monitoring import AlertItem, ErrorEvent, LogEntry, MonitoringData


class MonitoringService:
    """Service handling system monitoring, log retrieval, and error tracking."""

    def __init__(self) -> None:
        self.analytics_repo = AnalyticsRepository()
        self.system_repo = SystemRepository()

    def get_monitoring_data(self) -> MonitoringData:
        """Compile system monitoring payload."""
        logs_raw = self.analytics_repo.get_system_logs(limit=50)
        errors_raw = self.analytics_repo.get_recent_errors()

        logs = [LogEntry(**log_item) for log_item in logs_raw]
        errors = [ErrorEvent(**e) for e in errors_raw]
        alerts = [
            AlertItem(
                id="alt-1",
                timestamp="System Startup",
                severity="info",
                title="System Operational",
                message="REST API monitoring and log streaming active.",
                acknowledged=True,
            )
        ]

        return MonitoringData(
            logs=logs,
            errors=errors,
            alerts=alerts,
        )

    def get_filtered_logs(
        self,
        level: str | None = None,
        module: str | None = None,
        search: str | None = None,
        limit: int = 100,
    ) -> list[LogEntry]:
        """Fetch filtered runtime system logs."""
        logs_raw = self.analytics_repo.get_system_logs(
            level=level, module=module, search=search, limit=limit
        )
        return [LogEntry(**log_item) for log_item in logs_raw]

    def get_warnings(self) -> list[dict[str, Any]]:
        """Fetch runtime warning log entries."""
        return self.analytics_repo.get_recent_warnings()
