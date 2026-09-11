from __future__ import annotations

from pydantic import BaseModel


class SystemSettingsSchema(BaseModel):
    app_name: str
    environment: str
    primary_provider: str
    secondary_provider: str
    tertiary_provider: str
    groq_model_name: str
    gemini_model_name: str
    ollama_model: str
    embedding_model_name: str
    chunk_size: int
    chunk_overlap: int
    retrieval_top_k: int
    retrieval_min_similarity: float
    circuit_breaker_threshold: int
    circuit_breaker_cooldown: int


class SettingsUpdateSchema(BaseModel):
    primary_provider: str | None = None
    secondary_provider: str | None = None
    tertiary_provider: str | None = None
    chunk_size: int | None = None
    chunk_overlap: int | None = None
    retrieval_top_k: int | None = None
