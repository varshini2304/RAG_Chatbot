from __future__ import annotations

from app.api.repositories.analytics_repository import AnalyticsRepository
from app.api.repositories.provider_repository import ProviderRepository
from app.api.repositories.system_repository import SystemRepository
from app.api.schemas.dashboard import (
    ActivityItem,
    DashboardOverviewData,
    MetricItem,
    ProviderStatusSummary,
    SystemHealthSummary,
)


class DashboardService:
    """Service encapsulating dashboard business logic."""

    def __init__(self) -> None:
        self.system_repo = SystemRepository()
        self.provider_repo = ProviderRepository()
        self.analytics_repo = AnalyticsRepository()

    def get_overview(self) -> DashboardOverviewData:
        """Compile complete dashboard overview payload."""
        counts = self.analytics_repo.get_conversation_counts()
        hw_stats = self.system_repo.get_hardware_stats()
        chroma_stats = self.system_repo.get_chroma_status()
        prov_info = self.provider_repo.get_current_provider_info()
        activities = self.analytics_repo.get_recent_activities()
        trends = self.analytics_repo.get_trend_analytics()

        # Build dynamic 7-day sparkline series from real trend analytics
        conv_sparkline = [t["conversations"] for t in trends] or [0] * 7
        user_sparkline = [t["active_users"] for t in trends] or [0] * 7
        queries_sparkline = [t["requests"] for t in trends] or [0] * 7
        error_sparkline = [t["error_rate_pct"] for t in trends] or [0.0] * 7
        resp_sparkline = [t["response_time_sec"] for t in trends] or [0.5] * 7

        # Ensure sparkline has at least 7 points for smooth graph rendering
        def _pad_sparkline(
            arr: list[float | int], default_val: float
        ) -> list[float | int]:
            if not arr:
                return [default_val] * 7
            if len(arr) < 7:
                return [default_val] * (7 - len(arr)) + arr
            return arr

        conv_spark = _pad_sparkline(conv_sparkline, counts["total_conversations"])
        user_spark = _pad_sparkline(user_sparkline, counts["active_users"])
        queries_spark = _pad_sparkline(queries_sparkline, counts["avg_queries_per_day"])
        error_spark = _pad_sparkline(error_sparkline, counts["error_rate_pct"])
        resp_spark = _pad_sparkline(resp_sparkline, counts["avg_response_time_sec"])

        # Compute dynamic percentage / difference change strings
        def _calc_change(
            spark: list[float | int], suffix: str = "%"
        ) -> tuple[str, str, str]:
            if len(spark) >= 2 and spark[0] != 0:
                first = float(spark[0])
                last = float(spark[-1])
                pct = ((last - first) / first) * 100.0
                if pct >= 0:
                    return f"↑ {pct:.1f}{suffix} vs last 7 days", "up", "positive"
                return f"↓ {abs(pct):.1f}{suffix} vs last 7 days", "down", "negative"
            return "• 0.0% vs last 7 days", "neutral", "neutral"

        conv_change, conv_trend, conv_trend_type = _calc_change(conv_spark)
        user_change, user_trend, user_trend_type = _calc_change(user_spark)
        query_change, query_trend, query_trend_type = _calc_change(queries_spark)

        metrics = {
            "total_conversations": MetricItem(
                title="Total Conversations",
                value=f"{counts['total_conversations']:,}",
                change=conv_change,
                trend=conv_trend,
                trend_type=conv_trend_type,
                sparkline=conv_spark,
            ),
            "active_users": MetricItem(
                title="Active Users",
                value=f"{counts['active_users']:,}",
                change=user_change,
                trend=user_trend,
                trend_type=user_trend_type,
                sparkline=user_spark,
            ),
            "queries_per_day": MetricItem(
                title="Queries / Day (Avg)",
                value=f"{counts['avg_queries_per_day']:,}",
                change=query_change,
                trend=query_trend,
                trend_type=query_trend_type,
                sparkline=queries_spark,
            ),
            "error_rate": MetricItem(
                title="Error Rate",
                value=f"{counts['error_rate_pct']:.2f}%",
                change=(
                    "↓ 0.00% vs last 7 days"
                    if counts["error_rate_pct"] == 0
                    else f"↑ {counts['error_rate_pct']:.2f}% active errors"
                ),
                trend="down" if counts["error_rate_pct"] == 0 else "up",
                trend_type="positive" if counts["error_rate_pct"] == 0 else "negative",
                sparkline=error_spark,
            ),
            "avg_response_time": MetricItem(
                title="Avg. Response Time",
                value=f"{counts['avg_response_time_sec']:.2f}s",
                change=f"⚡ {counts['avg_response_time_sec']:.2f}s average latency",
                trend="down",
                trend_type="positive",
                sparkline=resp_spark,
            ),
        }

        system_health = SystemHealthSummary(
            api_status="healthy",
            vector_db_status=chroma_stats.get("status", "healthy"),
            embedding_status="healthy",
            ollama_server_status="running",
            cpu_usage_pct=hw_stats["cpu_percent"],
            memory_usage_pct=hw_stats["memory_percent"],
            disk_usage_pct=hw_stats["disk_percent"],
            chunk_count=chroma_stats.get("chunk_count", 0),
        )

        provider_status = ProviderStatusSummary(
            active_provider=prov_info["active_provider"],
            active_model=prov_info["active_model"],
            circuit_breaker_status=prov_info["circuit_breaker_status"],
            fallback_active=prov_info["fallback_active"],
            offline_mode=prov_info["offline_mode"],
        )

        recent_activities = [
            ActivityItem(
                id=act["id"],
                title=act["title"],
                timestamp=act["timestamp"],
                type=act["type"],
            )
            for act in activities
        ]

        return DashboardOverviewData(
            metrics=metrics,
            system_health=system_health,
            provider_status=provider_status,
            recent_activities=recent_activities,
        )
