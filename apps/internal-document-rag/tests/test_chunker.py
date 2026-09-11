"""Unit tests for RecursiveCharacterTextSplitter-based chunk generation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from app.ingestion.chunker import DocumentChunker
from app.ingestion.exceptions import ChunkingError, MetadataValidationError
from app.models.schemas import (
    ChunkMetadata,
    DocumentChunk,
    ExtractedPage,
    ExtractedPdfDocument,
)


def test_chunk_document_generates_multiple_chunks() -> None:
    """Chunking should split long page text into multiple semantic chunks."""
    extracted_document = ExtractedPdfDocument(
        source_file="handbook.pdf",
        file_path=Path("data/uploads/handbook.pdf"),
        document_type="pdf",
        pages=[
            ExtractedPage(
                page_number=1,
                content=" ".join(["policy update"] * 300),
            )
        ],
    )

    chunker = DocumentChunker(chunk_size=120, chunk_overlap=20)
    chunks = chunker.chunk_document(extracted_document)

    assert len(chunks) > 1
    assert all(chunk.content.strip() for chunk in chunks)


def test_chunk_document_handles_small_txt_document() -> None:
    """A small TXT document should remain a single chunk with preserved metadata."""
    extracted_document = ExtractedPdfDocument(
        source_file="notes.txt",
        file_path=Path("data/uploads/notes.txt"),
        document_type="txt",
        pages=[ExtractedPage(page_number=1, content="Short note for validation.")],
    )

    chunker = DocumentChunker(chunk_size=200, chunk_overlap=20)
    chunks = chunker.chunk_document(extracted_document)

    assert len(chunks) == 1
    assert chunks[0].content == "Short note for validation."
    assert chunks[0].metadata.document_type == "txt"
    assert chunks[0].metadata.page_number == 1


def test_chunk_document_splits_japanese_text_without_losing_cjk_punctuation() -> None:
    """Chunking should handle Japanese punctuation separators cleanly."""
    sentence = "これは日本語の文章です。"
    extracted_document = ExtractedPdfDocument(
        source_file="japanese.txt",
        file_path=Path("data/uploads/japanese.txt"),
        document_type="txt",
        pages=[ExtractedPage(page_number=1, content=sentence * 40)],
    )

    chunker = DocumentChunker(chunk_size=80, chunk_overlap=10)
    chunks = chunker.chunk_document(extracted_document)

    assert len(chunks) > 1
    assert all(chunk.content.strip() for chunk in chunks)
    assert any("。" in chunk.content for chunk in chunks)


def test_chunk_document_preserves_metadata() -> None:
    """Chunking should preserve file, page, chunk id, and document type metadata."""
    extracted_document = ExtractedPdfDocument(
        source_file="manual.pdf",
        file_path=Path("data/uploads/manual.pdf"),
        document_type="pdf",
        pages=[
            ExtractedPage(page_number=2, content="Security policy details " * 40),
        ],
    )

    chunker = DocumentChunker(chunk_size=100, chunk_overlap=10)
    chunks = chunker.chunk_document(extracted_document)

    first_chunk = chunks[0]
    assert first_chunk.metadata.source_file == "manual.pdf"
    assert first_chunk.metadata.page_number == 2
    assert first_chunk.metadata.document_type == "pdf"
    assert first_chunk.metadata.chunk_id == "manual.pdf-p2-c1"
    assert all(chunk.metadata.source_file == "manual.pdf" for chunk in chunks)
    assert all(chunk.metadata.document_type == "pdf" for chunk in chunks)


def test_chunk_document_rejects_document_without_pages() -> None:
    """Chunking should fail for documents that contain no extracted pages."""
    extracted_document = ExtractedPdfDocument(
        source_file="empty.pdf",
        file_path=Path("data/uploads/empty.pdf"),
        document_type="pdf",
        pages=[],
    )

    chunker = DocumentChunker()

    with pytest.raises(ChunkingError, match="no extracted pages"):
        chunker.chunk_document(extracted_document)


def test_chunker_rejects_invalid_overlap_configuration() -> None:
    """Chunker initialization should fail for invalid overlap values."""
    with pytest.raises(ChunkingError, match="smaller than chunk size"):
        DocumentChunker(chunk_size=100, chunk_overlap=100)


def test_chunk_document_preserves_page_order_and_association() -> None:
    """Chunks should remain ordered by page and keep the correct page association."""
    extracted_document = ExtractedPdfDocument(
        source_file="two-pages.pdf",
        file_path=Path("data/uploads/two-pages.pdf"),
        document_type="pdf",
        pages=[
            ExtractedPage(page_number=1, content="alpha " * 50),
            ExtractedPage(page_number=2, content="beta " * 50),
        ],
    )

    chunker = DocumentChunker(chunk_size=80, chunk_overlap=10)
    chunks = chunker.chunk_document(extracted_document)

    page_numbers = [chunk.metadata.page_number for chunk in chunks]
    assert page_numbers == sorted(page_numbers)
    assert all(
        "alpha" in chunk.content for chunk in chunks if chunk.metadata.page_number == 1
    )
    assert all(
        "beta" in chunk.content for chunk in chunks if chunk.metadata.page_number == 2
    )


def test_chunk_document_generates_unique_chunk_ids() -> None:
    """Each generated chunk_id should be unique across the full document."""
    extracted_document = ExtractedPdfDocument(
        source_file="ids.pdf",
        file_path=Path("data/uploads/ids.pdf"),
        document_type="pdf",
        pages=[
            ExtractedPage(page_number=1, content="gamma " * 80),
            ExtractedPage(page_number=2, content="delta " * 80),
        ],
    )

    chunker = DocumentChunker(chunk_size=90, chunk_overlap=15)
    chunks = chunker.chunk_document(extracted_document)
    chunk_ids = [chunk.metadata.chunk_id for chunk in chunks]

    assert len(chunk_ids) == len(set(chunk_ids))


def test_chunk_document_preserves_overlap_between_consecutive_chunks() -> None:
    """Consecutive chunks from one page should preserve the configured overlap."""
    extracted_document = ExtractedPdfDocument(
        source_file="overlap.pdf",
        file_path=Path("data/uploads/overlap.pdf"),
        document_type="pdf",
        pages=[
            ExtractedPage(page_number=1, content="abcdefghijklmnopqrstuvwxyz" * 10),
        ],
    )

    chunker = DocumentChunker(chunk_size=40, chunk_overlap=8)
    chunks = chunker.chunk_document(extracted_document)

    assert len(chunks) > 1
    assert chunks[0].content[-8:] == chunks[1].content[:8]


def test_chunk_document_preserves_content_without_loss_when_overlap_is_zero() -> None:
    """Chunk concatenation should preserve full content when overlap is disabled."""
    content = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 5
    extracted_document = ExtractedPdfDocument(
        source_file="continuity.pdf",
        file_path=Path("data/uploads/continuity.pdf"),
        document_type="pdf",
        pages=[ExtractedPage(page_number=1, content=content)],
    )

    chunker = DocumentChunker(chunk_size=30, chunk_overlap=0)
    chunks = chunker.chunk_document(extracted_document)

    reconstructed = "".join(chunk.content for chunk in chunks)
    assert reconstructed == content


def test_chunk_document_rejects_missing_source_file_metadata() -> None:
    """Chunking should fail when source_file is missing."""
    extracted_document = ExtractedPdfDocument.model_construct(
        source_file="",
        file_path=Path("data/uploads/missing.pdf"),
        document_type="pdf",
        pages=[ExtractedPage(page_number=1, content="epsilon " * 20)],
    )

    chunker = DocumentChunker()

    with pytest.raises(MetadataValidationError, match="missing source_file"):
        chunker.chunk_document(extracted_document)


def test_chunk_document_rejects_missing_document_type_metadata() -> None:
    """Chunking should fail when document_type is missing."""
    extracted_document = ExtractedPdfDocument.model_construct(
        source_file="missing-type.pdf",
        file_path=Path("data/uploads/missing-type.pdf"),
        document_type="",
        pages=[ExtractedPage(page_number=1, content="zeta " * 20)],
    )

    chunker = DocumentChunker()

    with pytest.raises(MetadataValidationError, match="missing document_type"):
        chunker.chunk_document(extracted_document)


def test_chunk_document_rejects_invalid_page_number_metadata() -> None:
    """Chunking should fail when page_number is invalid."""
    extracted_document = ExtractedPdfDocument.model_construct(
        source_file="invalid-page.pdf",
        file_path=Path("data/uploads/invalid-page.pdf"),
        document_type="pdf",
        pages=[ExtractedPage.model_construct(page_number=0, content="eta " * 20)],
    )

    chunker = DocumentChunker()

    with pytest.raises(MetadataValidationError, match="invalid page_number"):
        chunker.chunk_document(extracted_document)


def test_chunk_document_rejects_empty_chunk_id() -> None:
    """Chunking should fail when chunk_id generation returns an empty value."""
    extracted_document = ExtractedPdfDocument(
        source_file="empty-id.pdf",
        file_path=Path("data/uploads/empty-id.pdf"),
        document_type="pdf",
        pages=[ExtractedPage(page_number=1, content="theta " * 20)],
    )

    chunker = DocumentChunker(chunk_size=40, chunk_overlap=5)

    with (
        patch.object(DocumentChunker, "_build_chunk_id", return_value=""),
        pytest.raises(MetadataValidationError, match="empty chunk_id"),
    ):
        chunker.chunk_document(extracted_document)


def test_chunk_collection_validation_rejects_duplicate_chunk_ids() -> None:
    """Collection validation should reject duplicate chunk identifiers."""
    duplicate_chunk = DocumentChunk(
        content="chunk text",
        metadata=ChunkMetadata(
            source_file="dup.pdf",
            page_number=1,
            chunk_id="dup.pdf-p1-c1",
            document_type="pdf",
        ),
    )

    with pytest.raises(MetadataValidationError, match="duplicate chunk_id"):
        DocumentChunker._validate_chunk_collection([duplicate_chunk, duplicate_chunk])


def test_chunk_collection_validation_rejects_invalid_within_page_order() -> None:
    """Collection validation should reject chunks that move backward within a page."""
    chunk_one = DocumentChunk(
        content="chunk one",
        metadata=ChunkMetadata(
            source_file="order.pdf",
            page_number=1,
            chunk_id="order.pdf-p1-c2",
            document_type="pdf",
        ),
    )
    chunk_two = DocumentChunk(
        content="chunk two",
        metadata=ChunkMetadata(
            source_file="order.pdf",
            page_number=1,
            chunk_id="order.pdf-p1-c1",
            document_type="pdf",
        ),
    )

    with pytest.raises(ChunkingError, match="ordering validation failed"):
        DocumentChunker._validate_chunk_collection([chunk_one, chunk_two])


def test_chunk_document_emits_chunking_logs(caplog: pytest.LogCaptureFixture) -> None:
    """Chunking should emit start, metadata validation, and completion logs."""
    extracted_document = ExtractedPdfDocument(
        source_file="logs.pdf",
        file_path=Path("data/uploads/logs.pdf"),
        document_type="pdf",
        pages=[ExtractedPage(page_number=1, content="lambda " * 60)],
    )

    chunker = DocumentChunker(chunk_size=80, chunk_overlap=10)

    with caplog.at_level("INFO"):
        chunker.chunk_document(extracted_document)

    messages = [record.message for record in caplog.records]
    assert any("Starting chunk generation" in message for message in messages)
    assert any("Validated metadata for chunk" in message for message in messages)
    assert any("Created chunk" in message for message in messages)
    assert any("Chunking completed" in message for message in messages)
