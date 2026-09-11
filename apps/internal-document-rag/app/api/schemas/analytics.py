from __future__ import annotations

from pydantic import BaseModel, Field


class TrendPoint(BaseModel):
    date: str
    conversations: int = 0
    active_users: int = 0
    responseTime: float = 0.0
    response_time_sec: float = 0.0
    error_rate_pct: float = 0.0


class ProviderShareItem(BaseModel):
    name: str
    value: int
    share_pct: float = 0.0
    percentage: str = "0%"
    color: str = "#6D5DF6"


class AnalyticsData(BaseModel):
    trend_data: list[TrendPoint] = Field(default_factory=list)
    provider_shares: list[ProviderShareItem] = Field(default_factory=list)
    total_queries: int = 0
    avg_latency_sec: float = 0.0
