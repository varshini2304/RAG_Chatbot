from __future__ import annotations

from pydantic import BaseModel, Field


class LogEntry(BaseModel):
    id: str
    timestamp: str
    level: str  # INFO | WARN | ERROR | DEBUG
    module: str
    message: str
    details: str | None = None


class ErrorEvent(BaseModel):
    id: str
    timestamp: str
    level: str = "ERROR"
    module: str = "app.llm"
    type: str
    provider: str
    status: str  # Resolved | Retrying | Critical
    message: str
    detail: str | None = None


class AlertItem(BaseModel):
    id: str
    timestamp: str
    severity: str  # critical | warning | info
    title: str
    message: str
    acknowledged: bool = False


class MonitoringData(BaseModel):
    logs: list[LogEntry] = Field(default_factory=list)
    errors: list[ErrorEvent] = Field(default_factory=list)
    alerts: list[AlertItem] = Field(default_factory=list)
