"""
User Portal Chat Router
==========================
Provides RAG query and conversation session management for authenticated users.

The RAG query endpoint wraps the existing QueryService.process_question()
without modifying any retrieval, LLM, or context-building logic.

Conversation management wraps the existing ChatHistoryService.

Endpoints:
    POST   /api/v1/chat/query                — ask a question (RAG)
    GET    /api/v1/chat/sessions             — list saved conversations
    GET    /api/v1/chat/sessions/{id}        — get a conversation
    POST   /api/v1/chat/sessions             — save/update a conversation
    DELETE /api/v1/chat/sessions/{id}        — delete a conversation
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.schemas.base import ResponseModel
from app.api.schemas.chat import (
    ChatMessageItem,
    ChatQueryRequest,
    ChatQueryResponse,
    ChatSessionDetail,
    ChatSessionSummary,
    SaveSessionRequest,
    SourceReferenceResponse,
)
from app.api.user_auth.portal_user import get_portal_user
from app.models.query_result import QueryResultKind
from app.services.chat_history_service import (
    ChatHistoryLoadError,
    ChatHistorySaveError,
    ChatHistoryService,
)
from app.services.query_service import QueryService

LOGGER = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["User Portal — Chat"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _chunk_to_source(chunk: object) -> SourceReferenceResponse:
    """Convert a DocumentChunk to an API source reference."""
    meta = getattr(chunk, "metadata", None)
    return SourceReferenceResponse(
        content=getattr(chunk, "content", ""),
        source_file=getattr(meta, "source_file", "unknown") if meta else "unknown",
        page_number=int(getattr(meta, "page_number", 1)) if meta else 1,
        chunk_id=str(getattr(meta, "chunk_id", "")) if meta else "",
        document_type=str(getattr(meta, "document_type", "pdf")) if meta else "pdf",
    )


# ---------------------------------------------------------------------------
# RAG Query Endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/query",
    response_model=ResponseModel[ChatQueryResponse],
    summary="Ask a Question (RAG)",
    description=(
        "Submit a question to the user's document workspace. "
        "The backend runs retrieval + context building + LLM generation using the "
        "existing QueryService pipeline. "
        "No RAG logic is duplicated in this router — it is a thin HTTP wrapper."
    ),
)
def query(
    payload: ChatQueryRequest,
    current_user: str = Depends(get_portal_user),  # noqa: B008
) -> ResponseModel[ChatQueryResponse]:
    """Execute a RAG query for the authenticated user."""
    question = payload.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty.",
        )

    LOGGER.info("RAG query: user='%s', question=%r", current_user, question)

    try:
        result = QueryService.process_question(
            question=question,
            username=current_user,           # Always derived from JWT
            query_language=payload.query_language,
            bm25_index_manager=None,          # QueryService auto-loads BM25 per-user
            offline_mode=payload.offline_mode,
        )
    except Exception as exc:
        LOGGER.exception("QueryService failed for user '%s':", current_user)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query processing failed: {exc}",
        ) from exc

    sources = [_chunk_to_source(chunk) for chunk in result.retrieved_chunks]

    return ResponseModel(
        success=True,
        message="Query processed successfully",
        data=ChatQueryResponse(
            success=True,
            answer=result.answer,
            kind=result.kind.value,
            retrieved_chunk_count=len(result.retrieved_chunks),
            sources=sources,
            session_id=payload.session_id,
        ),
    )


# ---------------------------------------------------------------------------
# Conversation Session Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/sessions",
    response_model=ResponseModel[list[ChatSessionSummary]],
    summary="List Saved Conversations",
    description="Return all saved chat session summaries for the authenticated user.",
)
def list_sessions(
    current_user: str = Depends(get_portal_user),  # noqa: B008
) -> ResponseModel[list[ChatSessionSummary]]:
    """Return the list of saved chat sessions for the user."""
    try:
        raw_sessions = ChatHistoryService.load_user_chats(current_user)
    except ChatHistoryLoadError as exc:
        LOGGER.error("Failed to load sessions for user '%s': %s", current_user, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load chat history: {exc}",
        ) from exc

    summaries = [
        ChatSessionSummary(
            session_id=s["session_id"],
            title=s.get("title", "Untitled"),
            created_at=s.get("created_at", ""),
            updated_at=s.get("updated_at", ""),
        )
        for s in raw_sessions
    ]

    return ResponseModel(
        success=True,
        message="Chat sessions retrieved successfully",
        data=summaries,
    )


@router.get(
    "/sessions/{session_id}",
    response_model=ResponseModel[ChatSessionDetail],
    summary="Get a Conversation",
    description="Return the full message history for a specific chat session.",
)
def get_session(
    session_id: str,
    current_user: str = Depends(get_portal_user),  # noqa: B008
) -> ResponseModel[ChatSessionDetail]:
    """Return the full history of a specific chat session."""
    try:
        raw_sessions = ChatHistoryService.load_user_chats(current_user)
    except ChatHistoryLoadError as exc:
        LOGGER.error("Failed to load sessions for user '%s': %s", current_user, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load chat history: {exc}",
        ) from exc

    session = next(
        (s for s in raw_sessions if s.get("session_id") == session_id), None
    )
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )

    raw_history = session.get("chat_history", [])
    history_items = [
        ChatMessageItem(
            role=msg.get("role", "user"),
            content=msg.get("content", ""),
            timestamp=msg.get("timestamp"),
            sources=[
                {
                    "content": getattr(s, "content", "") if hasattr(s, "content") else s.get("content", ""),
                    "source_file": (
                        getattr(getattr(s, "metadata", None), "source_file", "unknown")
                        if hasattr(s, "metadata")
                        else s.get("metadata", {}).get("source_file", "unknown")
                    ),
                    "page_number": (
                        getattr(getattr(s, "metadata", None), "page_number", 1)
                        if hasattr(s, "metadata")
                        else s.get("metadata", {}).get("page_number", 1)
                    ),
                    "document_type": (
                        getattr(getattr(s, "metadata", None), "document_type", "pdf")
                        if hasattr(s, "metadata")
                        else s.get("metadata", {}).get("document_type", "pdf")
                    ),
                }
                for s in msg.get("sources", [])
            ],
        )
        for msg in raw_history
    ]

    return ResponseModel(
        success=True,
        message="Chat session retrieved successfully",
        data=ChatSessionDetail(
            session_id=session["session_id"],
            title=session.get("title", "Untitled"),
            created_at=session.get("created_at", ""),
            updated_at=session.get("updated_at", ""),
            chat_history=history_items,
        ),
    )


@router.post(
    "/sessions",
    response_model=ResponseModel[ChatSessionSummary],
    status_code=status.HTTP_201_CREATED,
    summary="Save or Update a Conversation",
    description="Save the current chat session to history (create or update).",
)
def save_session(
    payload: SaveSessionRequest,
    current_user: str = Depends(get_portal_user),  # noqa: B008
) -> ResponseModel[ChatSessionSummary]:
    """Save or update a chat session for the authenticated user."""
    # Convert API schema messages to raw dict format expected by ChatHistoryService
    raw_history = [
        {
            "role": msg.role,
            "content": msg.content,
            "timestamp": msg.timestamp or "",
            "sources": msg.sources,
        }
        for msg in payload.chat_history
    ]

    try:
        updated_chats = ChatHistoryService.save_current_chat_to_history(
            username=current_user,
            active_session_id=payload.session_id,
            chat_history=raw_history,
        )
    except (ChatHistoryLoadError, ChatHistorySaveError) as exc:
        LOGGER.error("Failed to save session for user '%s': %s", current_user, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save chat session: {exc}",
        ) from exc

    saved = next(
        (s for s in updated_chats if s.get("session_id") == payload.session_id), None
    )

    return ResponseModel(
        success=True,
        message="Chat session saved successfully",
        data=ChatSessionSummary(
            session_id=payload.session_id,
            title=saved.get("title", "Untitled") if saved else "Untitled",
            created_at=saved.get("created_at", "") if saved else "",
            updated_at=saved.get("updated_at", "") if saved else "",
        ),
    )


@router.delete(
    "/sessions/{session_id}",
    response_model=ResponseModel[dict],
    summary="Delete a Conversation",
    description="Permanently delete a saved chat session.",
)
def delete_session(
    session_id: str,
    current_user: str = Depends(get_portal_user),  # noqa: B008
) -> ResponseModel[dict]:
    """Delete a specific chat session for the authenticated user."""
    try:
        ChatHistoryService.delete_chat_session(
            username=current_user, session_id=session_id
        )
        LOGGER.info(
            "Chat session deleted: user='%s', session='%s'", current_user, session_id
        )
    except (ChatHistoryLoadError, ChatHistorySaveError) as exc:
        LOGGER.error(
            "Failed to delete session '%s' for user '%s': %s",
            session_id,
            current_user,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete chat session: {exc}",
        ) from exc

    return ResponseModel(
        success=True,
        message=f"Chat session '{session_id}' deleted successfully",
        data={"session_id": session_id},
    )
