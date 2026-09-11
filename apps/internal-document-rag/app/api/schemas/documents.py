"""Pydantic schemas for the user-portal documents API."""

from __future__ import annotations

from pydantic import BaseModel


class DocumentMetaResponse(BaseModel):
    """Metadata for one uploaded document."""

    filename: str
    document_type: str
    chunk_count: int
    embedding_status: str  # "pending" | "completed" | "failed"


class WorkspaceResponse(BaseModel):
    """Full workspace state for the authenticated user."""

    documents: list[DocumentMetaResponse]
    total_documents: int
    total_chunks: int


class DeleteDocumentResponse(BaseModel):
    """Response after deleting a single document."""

    success: bool
    filename: str
    message: str


class ClearWorkspaceResponse(BaseModel):
    """Response after clearing the entire workspace."""

    success: bool
    message: str


class UploadDocumentResponse(BaseModel):
    """Response after a successful document upload and ingestion."""

    success: bool
    filename: str
    chunk_count: int
    embedding_status: str
    message: str
