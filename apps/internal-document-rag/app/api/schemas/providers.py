from __future__ import annotations

from pydantic import BaseModel, Field


class ProviderInfo(BaseModel):
    id: str
    name: str
    model: str
    status: str
    latency: str = Field("0ms", alias="latency_str")
    latencyMs: float = Field(0.0, alias="latency_ms")
    requests: int = Field(0, alias="requests_total")
    failures: int = Field(0, alias="failures_total")
    successRate: str = Field("100%", alias="success_rate_pct")
    circuitBreakerState: str = Field("CLOSED", alias="circuit_breaker_status")
    isActive: bool = Field(False, alias="is_active")
    lastHealthCheck: str = Field("Just now", alias="last_health_check")

    class Config:
        populate_by_name = True


class ProvidersSummary(BaseModel):
    currentProvider: str = Field("groq", alias="current_provider")
    providers: list[ProviderInfo] = Field(default_factory=list)

    class Config:
        populate_by_name = True
