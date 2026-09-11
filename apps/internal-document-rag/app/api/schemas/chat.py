"""Pydantic schemas for the user-portal chat and conversation endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Chat query
# ---------------------------------------------------------------------------


class ChatQueryRequest(BaseModel):
    """Payload for POST /api/v1/chat/query."""

    question: str = Field(..., min_length=1, description="The user's question")
    query_language: str = Field(
        default="en",
        description="BCP-47 language code for the response language (e.g. 'en', 'ja')",
    )
    session_id: str | None = Field(
        default=None,
        description="Optional active session ID to associate this query with",
    )
    offline_mode: bool | None = Field(
        default=None,
        description="Optional offline mode override for this query",
    )


class SourceReferenceResponse(BaseModel):
    """One retrieved source chunk returned with the answer."""

    content: str
    source_file: str
    page_number: int
    chunk_id: str
    document_type: str


class ChatQueryResponse(BaseModel):
    """Returned by POST /api/v1/chat/query."""

    success: bool = True
    answer: str
    kind: str  # "success" | "insufficient_information" | "error"
    retrieved_chunk_count: int
    sources: list[SourceReferenceResponse]
    session_id: str | None = None


# ---------------------------------------------------------------------------
# Conversation sessions
# ---------------------------------------------------------------------------


class ChatMessageItem(BaseModel):
    """One turn in a conversation."""

    role: str  # "user" | "assistant"
    content: str
    timestamp: str | None = None
    sources: list[dict[str, Any]] = Field(default_factory=list)


class ChatSessionSummary(BaseModel):
    """Summary entry for the conversation list."""

    session_id: str
    title: str
    created_at: str
    updated_at: str


class ChatSessionDetail(ChatSessionSummary):
    """Full conversation session with message history."""

    chat_history: list[ChatMessageItem]


class SaveSessionRequest(BaseModel):
    """Payload for POST /api/v1/chat/sessions."""

    session_id: str = Field(..., description="Session ID to save or update")
    chat_history: list[ChatMessageItem] = Field(
        ..., description="Full conversation history"
    )
