"""
User Portal Documents Router
================================
Provides document management endpoints for the authenticated user.

All operations are scoped to the authenticated user's workspace.
The username is derived from the validated JWT — never from request params.

Endpoints:
    GET    /api/v1/documents            — list user's documents
    POST   /api/v1/documents/upload     — upload and ingest a document
    DELETE /api/v1/documents/{filename} — delete a single document
    DELETE /api/v1/documents/workspace  — clear the entire workspace
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.api.schemas.base import ErrorResponse, ResponseModel
from app.api.schemas.documents import (
    ClearWorkspaceResponse,
    DeleteDocumentResponse,
    DocumentMetaResponse,
    UploadDocumentResponse,
    WorkspaceResponse,
)
from app.api.user_auth.portal_user import get_portal_user
from app.config import settings
from app.models.schemas import ExtractedPdfDocument
from app.retrieval.bm25_index_manager import BM25IndexManager
from app.services.upload_service import UploadService
from app.services.workspace_service import WorkspaceService
from app.vectorstore.chroma_manager import ChromaVectorStore

LOGGER = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["User Portal — Documents"])


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_embedding_model():
    """Load the singleton embedding model (same as Streamlit version)."""
    from app.embeddings.embedding_model_loader import load_embedding_model

    return load_embedding_model(settings.embedding_model_name)


def _get_vector_store(username: str) -> ChromaVectorStore:
    """Return a per-user ChromaDB vector store instance."""
    collection_name = WorkspaceService.get_collection_name(username)
    return ChromaVectorStore(collection_name=collection_name)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=ResponseModel[WorkspaceResponse],
    summary="List User Documents",
    description="Return all documents in the authenticated user's workspace.",
)
def list_documents(
    current_user: str = Depends(get_portal_user),  # noqa: B008
) -> ResponseModel[WorkspaceResponse]:
    """Load and return the user's workspace document list."""
    try:
        workspace = WorkspaceService.load_workspace(current_user)
    except Exception as exc:
        LOGGER.exception("Failed to load workspace for user '%s':", current_user)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load workspace: {exc}",
        ) from exc

    doc_responses: list[DocumentMetaResponse] = []
    total_chunks = 0

    for doc in workspace.documents:
        chunks = workspace.chunks.get(doc.source_file, [])
        emb_status = workspace.embedding_status.get(doc.source_file, "pending")
        chunk_count = len(chunks)
        total_chunks += chunk_count
        doc_responses.append(
            DocumentMetaResponse(
                filename=doc.source_file,
                document_type=doc.document_type,
                chunk_count=chunk_count,
                embedding_status=emb_status,
            )
        )

    return ResponseModel(
        success=True,
        message="Documents loaded successfully",
        data=WorkspaceResponse(
            documents=doc_responses,
            total_documents=len(doc_responses),
            total_chunks=total_chunks,
        ),
    )


@router.post(
    "/upload",
    response_model=ResponseModel[UploadDocumentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload and Ingest a Document",
    description=(
        "Upload a document file (PDF, TXT, PNG, JPG, JPEG, WEBP, TIFF, BMP). "
        "The file is extracted, chunked, embedded, and indexed into the user's "
        "workspace. This calls the existing ingestion pipeline unchanged."
    ),
)
async def upload_document(
    file: UploadFile = File(...),
    current_user: str = Depends(get_portal_user),  # noqa: B008
) -> ResponseModel[UploadDocumentResponse] | JSONResponse:
    """Upload a file, run the full ingestion pipeline, and return results."""

    # --- Validate extension ---
    if not file.filename:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                success=False,
                message="No filename provided.",
                errors=["No filename provided."],
            ).model_dump(),
        )

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in settings.allowed_upload_extensions:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                success=False,
                message=f"Unsupported file type: .{ext}",
                errors=[f"Unsupported file type: .{ext}"],
            ).model_dump(),
        )

    # --- Validate file size ---
    contents = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(contents) > max_bytes:
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content=ErrorResponse(
                success=False,
                message=f"File exceeds the {settings.max_upload_size_mb} MB limit.",
                errors=[f"File size exceeds {settings.max_upload_size_mb} MB."],
            ).model_dump(),
        )

    # --- Build an in-memory file object compatible with UploadService ---
    class _ApiUploadedFile:
        """Adapter to make an UploadFile compatible with UploadService.extract_document."""

        def __init__(self, name: str, data: bytes) -> None:
            self.name = name
            self._data = data

        def getvalue(self) -> bytes:
            return self._data

        def getbuffer(self) -> memoryview:
            return memoryview(self._data)

        def read(self, size: int = -1) -> bytes:
            return self._data if size < 0 else self._data[:size]

    upload_obj = _ApiUploadedFile(name=file.filename, data=contents)

    # --- Run full ingestion pipeline (extract → chunk → embed → index) ---
    try:
        extracted_doc: ExtractedPdfDocument = UploadService.extract_document(
            current_user, upload_obj
        )
    except ValueError as exc:
        # Includes duplicate-detection and validation errors
        error_str = str(exc)
        LOGGER.warning(
            "Upload rejected for user '%s', file '%s': %s",
            current_user,
            file.filename,
            error_str,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                success=False,
                message=error_str,
                errors=[error_str],
            ).model_dump(),
        )
    except Exception as exc:
        LOGGER.exception(
            "Extraction failed for user '%s', file '%s':", current_user, file.filename
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                success=False,
                message=f"Document extraction failed: {exc}",
                errors=[str(exc)],
            ).model_dump(),
        )

    try:
        chunks = UploadService.chunk_document(extracted_doc)
    except Exception as exc:
        LOGGER.exception(
            "Chunking failed for user '%s', file '%s':", current_user, file.filename
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                success=False,
                message=f"Document chunking failed: {exc}",
                errors=[str(exc)],
            ).model_dump(),
        )

    if not chunks:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                success=False,
                message="No content could be extracted from the document.",
                errors=["Empty document — no chunks generated."],
            ).model_dump(),
        )

    try:
        embedding_model = _get_embedding_model()
        vector_store = _get_vector_store(current_user)
        UploadService.embed_and_index(
            chunks=chunks,
            embedding_model=embedding_model,
            vector_store=vector_store,
        )
        embedding_status = "completed"
    except Exception as exc:
        LOGGER.exception(
            "Embedding failed for user '%s', file '%s':", current_user, file.filename
        )
        embedding_status = "failed"
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                success=False,
                message=f"Embedding pipeline failed: {exc}",
                errors=[str(exc)],
            ).model_dump(),
        )

    LOGGER.info(
        "Document ingested: user='%s', file='%s', chunks=%d",
        current_user,
        file.filename,
        len(chunks),
    )

    return ResponseModel(
        success=True,
        message="Document uploaded and indexed successfully.",
        data=UploadDocumentResponse(
            success=True,
            filename=file.filename,
            chunk_count=len(chunks),
            embedding_status=embedding_status,
            message="Document uploaded and indexed successfully.",
        ),
    )


@router.delete(
    "/workspace",
    response_model=ResponseModel[ClearWorkspaceResponse],
    summary="Clear Entire Workspace",
    description=(
        "Delete all documents, vectors, and hashes from the authenticated user's "
        "workspace. This action is irreversible."
    ),
)
def clear_workspace(
    current_user: str = Depends(get_portal_user),  # noqa: B008
) -> ResponseModel[ClearWorkspaceResponse]:
    """Clear all documents for the authenticated user."""
    try:
        # Clear BM25 index
        bm25 = BM25IndexManager(username=current_user)
        try:
            bm25.clear()
        except Exception as exc:
            LOGGER.warning("BM25 clear failed for user '%s': %s", current_user, exc)

        # Clear workspace (files + ChromaDB)
        WorkspaceService.clear_workspace(current_user)
        LOGGER.info("Workspace cleared for user: %s", current_user)
    except Exception as exc:
        LOGGER.exception("Failed to clear workspace for user '%s':", current_user)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear workspace: {exc}",
        ) from exc

    return ResponseModel(
        success=True,
        message="Workspace cleared successfully.",
        data=ClearWorkspaceResponse(
            success=True,
            message="All documents have been removed from your workspace.",
        ),
    )


@router.delete(
    "/{filename}",
    response_model=ResponseModel[DeleteDocumentResponse],
    summary="Delete a Document",
    description=(
        "Remove a single document from the authenticated user's workspace. "
        "Deletes the file, its vector embeddings, BM25 index entries, and hash records."
    ),
)
def delete_document(
    filename: str,
    current_user: str = Depends(get_portal_user),  # noqa: B008
) -> ResponseModel[DeleteDocumentResponse]:
    """Delete a single document for the authenticated user."""

    # --- Sanitize filename to prevent path traversal ---
    safe_filename = filename.replace("/", "_").replace("\\", "_").replace("..", "_")
    if safe_filename != filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename.",
        )

    try:
        # Remove from BM25 index
        bm25 = BM25IndexManager(username=current_user)
        try:
            bm25.load()
            bm25.remove_document_by_source(filename)
        except Exception as exc:
            LOGGER.warning(
                "BM25 remove failed for file '%s', user '%s': %s",
                filename,
                current_user,
                exc,
            )

        # Delete file + ChromaDB chunks + hash registry
        WorkspaceService.delete_document(current_user, filename)
        LOGGER.info("Document deleted: user='%s', file='%s'", current_user, filename)
    except Exception as exc:
        LOGGER.exception(
            "Failed to delete document '%s' for user '%s':", filename, current_user
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {exc}",
        ) from exc

    return ResponseModel(
        success=True,
        message=f"Document '{filename}' deleted successfully.",
        data=DeleteDocumentResponse(
            success=True,
            filename=filename,
            message=f"Document '{filename}' has been removed from your workspace.",
        ),
    )
