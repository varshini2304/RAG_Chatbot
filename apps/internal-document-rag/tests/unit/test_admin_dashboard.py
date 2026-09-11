"""Unit tests for Admin Console Dashboard services and telemetry repositories."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.api.repositories.system_repository import SystemRepository
from app.api.services.dashboard_service import DashboardService


def test_system_repository_fetches_hardware_telemetry() -> None:
    """SystemRepository should query psutil and return CPU, Memory, Disk utilization metrics."""
    with (
        patch("psutil.cpu_percent", return_value=15.5),
        patch("psutil.virtual_memory") as mock_mem,
        patch("psutil.disk_usage") as mock_disk,
    ):

        mock_mem.return_value = MagicMock(percent=45.2)
        mock_disk.return_value = MagicMock(percent=60.1)

        repo = SystemRepository()
        stats = repo.get_hardware_stats()

        assert stats["cpu_percent"] == 15.5
        assert stats["memory_percent"] == 45.2
        assert stats["disk_percent"] == 60.1


def test_dashboard_service_compiles_overview() -> None:
    """DashboardService should compile overview payload."""
    with (
        patch("app.api.services.dashboard_service.SystemRepository") as mock_sys_cls,
        patch("app.api.services.dashboard_service.ProviderRepository") as mock_prov_cls,
        patch(
            "app.api.services.dashboard_service.AnalyticsRepository"
        ) as mock_analytics_cls,
    ):

        mock_sys = mock_sys_cls.return_value
        mock_sys.get_hardware_stats.return_value = {
            "cpu_percent": 20.0,
            "memory_percent": 40.0,
            "disk_percent": 50.0,
        }
        mock_sys.get_chroma_status.return_value = {
            "status": "healthy",
            "chunk_count": 100,
        }

        mock_analytics = mock_analytics_cls.return_value
        mock_analytics.get_conversation_counts.return_value = {
            "total_conversations": 42,
            "active_users": 5,
            "avg_queries_per_day": 10,
            "avg_response_time_sec": 1.2,
            "error_rate_pct": 0.1,
        }
        mock_analytics.get_recent_activities.return_value = []

        mock_prov = mock_prov_cls.return_value
        mock_prov.get_current_provider_info.return_value = {
            "active_provider": "Groq Cloud",
            "active_model": "llama-3.3-70b-versatile",
            "circuit_breaker_status": "CLOSED",
            "fallback_active": False,
            "offline_mode": False,
        }

        service = DashboardService()
        data = service.get_overview()
        assert data.metrics is not None
        assert data.providerStatus.activeProvider == "Groq Cloud"
