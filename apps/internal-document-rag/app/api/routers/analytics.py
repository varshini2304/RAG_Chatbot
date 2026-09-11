from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.schemas.analytics import AnalyticsData, ProviderShareItem, TrendPoint
from app.api.schemas.base import ResponseModel
from app.api.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def get_analytics_service() -> AnalyticsService:
    return AnalyticsService()


@router.get("", response_model=ResponseModel[AnalyticsData])
def get_all_analytics(
    service: AnalyticsService = Depends(get_analytics_service),
) -> ResponseModel[AnalyticsData]:
    """Retrieve full analytics datasets."""
    data = service.get_analytics()
    return ResponseModel(
        success=True,
        message="Analytics data retrieved successfully",
        data=data,
    )


@router.get("/conversations", response_model=ResponseModel[list[TrendPoint]])
def get_conversation_analytics(
    time_frame: str = Query(
        "daily", description="Aggregation timeframe: daily | weekly"
    ),
    service: AnalyticsService = Depends(get_analytics_service),
) -> ResponseModel[list[TrendPoint]]:
    """Retrieve conversation volume trends over time."""
    data = service.get_analytics().trend_data
    return ResponseModel(
        success=True,
        message="Conversation analytics retrieved successfully",
        data=data,
    )


@router.get("/provider-usage", response_model=ResponseModel[list[ProviderShareItem]])
def get_provider_usage_analytics(
    service: AnalyticsService = Depends(get_analytics_service),
) -> ResponseModel[list[ProviderShareItem]]:
    """Retrieve provider usage ratios (Groq / Gemini / Ollama)."""
    data = service.get_analytics().provider_shares
    return ResponseModel(
        success=True,
        message="Provider usage analytics retrieved successfully",
        data=data,
    )


@router.get("/response-time", response_model=ResponseModel[dict[str, Any]])
def get_response_time_analytics(
    service: AnalyticsService = Depends(get_analytics_service),
) -> ResponseModel[dict[str, Any]]:
    """Retrieve average response latencies."""
    analytics = service.get_analytics()
    return ResponseModel(
        success=True,
        message="Response time analytics retrieved successfully",
        data={
            "avg_latency_sec": analytics.avg_latency_sec,
            "trend": analytics.trend_data,
        },
    )
