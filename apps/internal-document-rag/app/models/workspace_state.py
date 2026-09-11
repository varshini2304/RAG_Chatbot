from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.models.schemas import DocumentChunk, ExtractedPdfDocument

if TYPE_CHECKING:
    from app.retrieval.bm25_index_manager import BM25IndexManager


@dataclass
class WorkspaceState:
    """Contains all isolated document, hash, and status metadata for a user session."""

    documents: list[ExtractedPdfDocument]
    hashes: dict[str, str]
    embedding_status: dict[str, str]
    processed_names: set[str]
    document_errors: dict[str, str]
    chunks: dict[str, list[DocumentChunk]]
    bm25_index_manager: BM25IndexManager | None = None
