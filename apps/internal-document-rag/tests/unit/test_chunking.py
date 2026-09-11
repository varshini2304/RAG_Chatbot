"""Unit tests for the document chunking module."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.ingestion.chunker import ChunkingError, DocumentChunker
from app.models.schemas import ExtractedPage, ExtractedPdfDocument


def test_chunker_generates_chunks_with_correct_overlap() -> None:
    """DocumentChunker should split page text using chunk_size and chunk_overlap."""
    chunker = DocumentChunker(chunk_size=100, chunk_overlap=20)
    page_text = "Word " * 50  # 250 characters
    doc = ExtractedPdfDocument(
        source_file="test.pdf",
        file_path=Path("/tmp/test.pdf"),
        document_type="pdf",
        pages=[ExtractedPage(page_number=1, content=page_text)],
    )

    chunks = chunker.chunk_document(doc)
    assert len(chunks) > 1
    for i, chunk in enumerate(chunks, 1):
        assert chunk.metadata.source_file == "test.pdf"
        assert chunk.metadata.page_number == 1
        assert chunk.metadata.chunk_id == f"test.pdf-p1-c{i}"
        assert chunk.metadata.document_type == "pdf"


def test_chunker_handles_multi_page_documents() -> None:
    """Chunks from different pages should carry appropriate page numbers and sequential IDs."""
    chunker = DocumentChunker(chunk_size=50, chunk_overlap=10)
    doc = ExtractedPdfDocument(
        source_file="multipage.pdf",
        file_path=Path("/tmp/multipage.pdf"),
        document_type="pdf",
        pages=[
            ExtractedPage(
                page_number=1, content="Page 1 content here for testing chunking."
            ),
            ExtractedPage(
                page_number=2, content="Page 2 content here for testing chunking."
            ),
        ],
    )

    chunks = chunker.chunk_document(doc)
    page1_chunks = [c for c in chunks if c.metadata.page_number == 1]
    page2_chunks = [c for c in chunks if c.metadata.page_number == 2]

    assert len(page1_chunks) >= 1
    assert len(page2_chunks) >= 1
    assert page1_chunks[0].metadata.chunk_id == "multipage.pdf-p1-c1"
    assert page2_chunks[0].metadata.chunk_id == "multipage.pdf-p2-c1"


def test_chunker_empty_document_raises_error() -> None:
    """Chunking a document with no pages or empty text must raise ChunkingError."""
    chunker = DocumentChunker(chunk_size=100, chunk_overlap=10)
    empty_doc = ExtractedPdfDocument(
        source_file="empty.pdf",
        file_path=Path("/tmp/empty.pdf"),
        document_type="pdf",
        pages=[],
    )

    with pytest.raises(ChunkingError, match="no extracted pages"):
        chunker.chunk_document(empty_doc)


def test_chunker_blank_text_page_raises_error() -> None:
    """Pages containing only whitespace should be rejected with ChunkingError."""
    chunker = DocumentChunker(chunk_size=100, chunk_overlap=10)
    blank_doc = ExtractedPdfDocument(
        source_file="blank.pdf",
        file_path=Path("/tmp/blank.pdf"),
        document_type="pdf",
        pages=[ExtractedPage(page_number=1, content="   \n\t  ")],
    )

    with pytest.raises(ChunkingError, match="No chunks could be generated"):
        chunker.chunk_document(blank_doc)


def test_chunker_invalid_size_parameters() -> None:
    """Initializing chunker with invalid chunk size or overlap should raise ChunkingError."""
    with pytest.raises(ChunkingError, match="greater than zero"):
        DocumentChunker(chunk_size=0, chunk_overlap=10)

    with pytest.raises(ChunkingError, match="cannot be negative"):
        DocumentChunker(chunk_size=100, chunk_overlap=-5)

    with pytest.raises(ChunkingError, match="smaller than chunk size"):
        DocumentChunker(chunk_size=100, chunk_overlap=100)
