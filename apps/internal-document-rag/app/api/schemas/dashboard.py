from __future__ import annotations

from pydantic import BaseModel, Field


class MetricItem(BaseModel):
    title: str
    value: str | int | float
    change: str
    trend: str = "up"
    trendType: str = Field("positive", alias="trend_type")
    sparkline: list[float] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class SystemHealthSummary(BaseModel):
    apiStatus: str = Field("healthy", alias="api_status")
    chromaDb: str = Field("healthy", alias="vector_db_status")
    embeddingService: str = Field("healthy", alias="embedding_status")
    ollamaServer: str = Field("running", alias="ollama_server_status")
    cpuUsage: float = Field(0.0, alias="cpu_usage_pct")
    memoryUsage: float = Field(0.0, alias="memory_usage_pct")
    diskUsage: float = Field(0.0, alias="disk_usage_pct")
    chunkCount: int = Field(0, alias="chunk_count")

    class Config:
        populate_by_name = True


class ProviderStatusSummary(BaseModel):
    activeProvider: str = Field("Ollama Server", alias="active_provider")
    activeModel: str = Field("qwen2.5:3b", alias="active_model")
    circuitBreakerStatus: str = Field("CLOSED", alias="circuit_breaker_status")
    fallbackActive: bool = Field(True, alias="fallback_active")
    offlineMode: bool = Field(True, alias="offline_mode")

    class Config:
        populate_by_name = True


class ActivityItem(BaseModel):
    id: str
    title: str
    timestamp: str
    type: str = "info"


class DashboardOverviewData(BaseModel):
    metrics: dict[str, MetricItem]
    systemHealth: SystemHealthSummary = Field(..., alias="system_health")
    providerStatus: ProviderStatusSummary = Field(..., alias="provider_status")
    recentActivities: list[ActivityItem] = Field(
        default_factory=list, alias="recent_activities"
    )

    class Config:
        populate_by_name = True
