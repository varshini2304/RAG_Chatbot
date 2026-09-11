"""
User Portal Workspace Status Router
======================================
Provides read-only workspace status for the authenticated user.

This exposes only information that is derivable from actual persisted state
(files on disk + ChromaDB metadata). It does NOT invent or synthesize metrics.

NOTE: In the Streamlit version, pipeline_status lived in st.session_state and
was built up incrementally during processing. In this API version, it is
derived statically from the loaded workspace state (whether documents exist,
whether chunks exist, whether embeddings are completed). This is functionally
equivalent to the Streamlit post-login state.

Endpoint:
    GET /api/v1/workspace/status
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.schemas.base import ResponseModel
from app.api.schemas.workspace import (
    PipelineStatusResponse,
    ProviderInfoResponse,
    WorkspaceStatusResponse,
)
from app.api.user_auth.portal_user import get_portal_user
from app.config import settings
from app.services.workspace_service import WorkspaceService

LOGGER = logging.getLogger(__name__)

router = APIRouter(prefix="/workspace", tags=["User Portal — Workspace"])


def _get_current_provider_info() -> ProviderInfoResponse:
    """
    Derive provider info from the application configuration and LLM router.

    This reads the currently active provider from the LLM router if possible,
    otherwise falls back to the static settings. We never expose per-user
    session state because that would create a global state leak between users.
    """
    try:
        from app.llm import get_llm_provider

        provider = get_llm_provider()
        provider_name = getattr(provider, "provider_name", settings.primary_provider)
        model_name = getattr(provider, "model_name", "")
        offline_mode = (
            provider.is_offline_mode_active()
            if hasattr(provider, "is_offline_mode_active")
            else settings.offline_mode
        )
    except Exception:
        provider_name = settings.primary_provider
        model_name = ""
        offline_mode = settings.offline_mode

    # Resolve model name from settings if not provided by provider
    if not model_name:
        prov_lower = provider_name.lower()
        if "groq" in prov_lower:
            model_name = settings.groq_model_name
        elif "gemini" in prov_lower:
            model_name = settings.gemini_model_name
        elif "ollama" in prov_lower:
            model_name = settings.ollama_model
        else:
            model_name = "unknown"

    return ProviderInfoResponse(
        current_provider=provider_name.capitalize(),
        current_model=model_name,
        fallback_active=False,  # Cannot derive from persisted state — always false at load
        offline_mode=offline_mode,
    )


@router.get(
    "/status",
    response_model=ResponseModel[WorkspaceStatusResponse],
    summary="Workspace Status",
    description=(
        "Return the current status of the authenticated user's workspace. "
        "Includes document count, total chunks, pipeline step completion flags, "
        "and current LLM provider information. "
        "All data is derived from persisted state — no fabricated metrics."
    ),
)
def workspace_status(
    current_user: str = Depends(get_portal_user),  # noqa: B008
) -> ResponseModel[WorkspaceStatusResponse]:
    """Return workspace status for the authenticated user."""
    try:
        workspace = WorkspaceService.load_workspace(current_user)
    except Exception as exc:
        LOGGER.exception("Failed to load workspace for user '%s':", current_user)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load workspace: {exc}",
        ) from exc

    # Derive pipeline status from workspace (mirrors Streamlit post-login logic)
    has_docs = bool(workspace.documents)
    has_chunks = has_docs and all(
        workspace.chunks.get(d.source_file) for d in workspace.documents
    )
    indexable_statuses = [
        workspace.embedding_status.get(d.source_file, "pending")
        for d in workspace.documents
        if workspace.embedding_status.get(d.source_file) != "failed"
    ]
    all_embedded = (
        has_docs
        and bool(indexable_statuses)
        and all(s == "completed" for s in indexable_statuses)
    )

    pipeline_status = PipelineStatusResponse(
        text_extraction=has_docs,
        chunking=has_chunks,
        embeddings=all_embedded,
        vector_store=all_embedded,
    )

    # Count total chunks
    total_chunks = sum(
        len(chunks) for chunks in workspace.chunks.values()
    )

    provider_info = _get_current_provider_info()

    return ResponseModel(
        success=True,
        message="Workspace status retrieved successfully",
        data=WorkspaceStatusResponse(
            document_count=len(workspace.documents),
            total_chunks=total_chunks,
            pipeline_status=pipeline_status,
            provider_info=provider_info,
            embedding_status=workspace.embedding_status,
        ),
    )
