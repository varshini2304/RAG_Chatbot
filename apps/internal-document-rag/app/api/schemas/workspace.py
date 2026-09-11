"""Pydantic schemas for workspace status API."""

from __future__ import annotations

from pydantic import BaseModel


class PipelineStatusResponse(BaseModel):
    """Processing pipeline step status flags."""

    text_extraction: bool = False
    chunking: bool = False
    embeddings: bool = False
    vector_store: bool = False


class ProviderInfoResponse(BaseModel):
    """Current LLM provider information."""

    current_provider: str
    current_model: str
    fallback_active: bool = False
    offline_mode: bool = False


class WorkspaceStatusResponse(BaseModel):
    """Full workspace status for the authenticated user."""

    document_count: int
    total_chunks: int
    pipeline_status: PipelineStatusResponse
    provider_info: ProviderInfoResponse
    embedding_status: dict[str, str]  # filename → "pending" | "completed" | "failed"
