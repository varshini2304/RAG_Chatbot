"""Integration test for Workflow 1: Document Upload -> Extraction -> Chunking -> Embedding -> ChromaDB Storage."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.embeddings.embedding_pipeline import EmbeddingPipeline
from app.ingestion.chunker import DocumentChunker
from app.ingestion.upload_pipeline import UploadPipeline
from app.models.schemas import ExtractedPage, ExtractedPdfDocument


class DummyUploadedFile:
    """Mock uploaded file implementing UploadedFileProtocol."""

    def __init__(self, name: str, content: bytes) -> None:
        self.name = name
        self.size = len(content)
        self._content = content

    def getbuffer(self) -> memoryview:
        return memoryview(self._content)


class DummyPDFLoader:
    def extract(self, file_path: Path) -> ExtractedPdfDocument:
        return ExtractedPdfDocument(
            source_file=file_path.name,
            file_path=file_path,
            document_type="pdf",
            pages=[
                ExtractedPage(
                    page_number=1,
                    content="Company Policy: Working hours are 9 AM to 5 PM EST. Paid vacation is 20 days per year.",
                )
            ],
        )


def test_complete_upload_to_chromadb_ingestion_pipeline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test integrated ingestion pipeline: File Upload -> Extracted Document -> Chunks -> Embeddings -> ChromaDB."""
    upload_dir = tmp_path / "uploads"
    chroma_dir = tmp_path / "chroma"
    upload_dir.mkdir()
    chroma_dir.mkdir()

    # 1. Setup UploadPipeline
    monkeypatch.setattr(
        "app.ingestion.upload_pipeline.settings",
        SimpleNamespace(
            upload_dir=upload_dir,
            allowed_upload_extensions=("pdf", "txt"),
            max_upload_size_mb=10,
        ),
    )
    pipeline = UploadPipeline()
    pipeline._pdf_loader = DummyPDFLoader()  # type: ignore[assignment]

    # 2. Process Upload
    uploaded_file = DummyUploadedFile("policy.pdf", b"Dummy PDF bytes")
    extracted_doc = pipeline.process_upload(uploaded_file)
    assert extracted_doc.source_file == "policy.pdf"

    # 3. Chunk Document
    chunker = DocumentChunker(chunk_size=100, chunk_overlap=20)
    chunks = chunker.chunk_document(extracted_doc)
    assert len(chunks) >= 1
    assert chunks[0].metadata.source_file == "policy.pdf"

    # 4. Generate Embeddings & Store in ChromaDB
    mock_service = MagicMock()
    mock_store = MagicMock()
    mock_service.generate_embeddings.return_value = [[0.1] * 384 for _ in chunks]
    mock_store.add_chunks.return_value = [c.metadata.chunk_id for c in chunks]

    embedding_pipeline = EmbeddingPipeline(
        embedding_service=mock_service, vector_store=mock_store
    )
    result_ids = embedding_pipeline.run(chunks)

    assert len(result_ids) == len(chunks)
    mock_service.generate_embeddings.assert_called_once()
    mock_store.add_chunks.assert_called_once()
