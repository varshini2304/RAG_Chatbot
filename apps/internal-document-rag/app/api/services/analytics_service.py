from __future__ import annotations

from app.api.repositories.analytics_repository import AnalyticsRepository
from app.api.schemas.analytics import AnalyticsData, ProviderShareItem, TrendPoint


class AnalyticsService:
    """Service handling analytics queries and aggregations."""

    def __init__(self) -> None:
        self.repo = AnalyticsRepository()

    def get_analytics(self) -> AnalyticsData:
        """Compile usage trends and provider distributions."""
        trends_raw = self.repo.get_trend_analytics()
        shares_raw = self.repo.get_provider_shares()
        counts = self.repo.get_conversation_counts()

        trend_points = [TrendPoint(**t) for t in trends_raw]
        provider_shares = [ProviderShareItem(**p) for p in shares_raw]

        return AnalyticsData(
            trend_data=trend_points,
            provider_shares=provider_shares,
            total_queries=counts["total_conversations"],
            avg_latency_sec=counts["avg_response_time_sec"],
        )
