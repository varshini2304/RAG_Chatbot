"""Unit tests for document upload pipeline, loaders, and validation."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.ingestion.exceptions import FileValidationError
from app.ingestion.upload_pipeline import UploadPipeline
from app.models.schemas import ExtractedPage, ExtractedPdfDocument


class DummyUploadedFile:
    """Mock uploaded file object implementing UploadedFileProtocol."""

    def __init__(self, name: str, content: bytes) -> None:
        self.name = name
        self.size = len(content)
        self._content = content

    def getbuffer(self) -> memoryview:
        return memoryview(self._content)


class DummyPDFLoader:
    """Mock PDF extraction loader."""

    def extract(self, file_path: Path) -> ExtractedPdfDocument:
        return ExtractedPdfDocument(
            source_file=file_path.name,
            file_path=file_path,
            document_type="pdf",
            pages=[ExtractedPage(page_number=1, content=file_path.read_text())],
        )


class DummyTextLoader:
    """Mock TXT extraction loader."""

    def extract(self, file_path: Path) -> ExtractedPdfDocument:
        return ExtractedPdfDocument(
            source_file=file_path.name,
            file_path=file_path,
            document_type="txt",
            pages=[ExtractedPage(page_number=1, content=file_path.read_text())],
        )


def _build_test_pipeline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> UploadPipeline:
    monkeypatch.setattr(
        "app.ingestion.upload_pipeline.settings",
        SimpleNamespace(
            upload_dir=tmp_path,
            allowed_upload_extensions=("pdf", "txt"),
            max_upload_size_mb=10,
        ),
    )
    pipeline = UploadPipeline()
    pipeline._pdf_loader = DummyPDFLoader()  # type: ignore[assignment]
    pipeline._text_loader = DummyTextLoader()  # type: ignore[assignment]
    return pipeline


def test_upload_single_pdf_document(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Valid PDF upload should save file and extract content."""
    pipeline = _build_test_pipeline(tmp_path, monkeypatch)
    uploaded = DummyUploadedFile("handbook.pdf", b"Company Handbook Text")

    doc = pipeline.process_upload(uploaded)
    assert doc.source_file == "handbook.pdf"
    assert doc.document_type == "pdf"
    assert len(doc.pages) == 1
    assert doc.pages[0].content == "Company Handbook Text"


def test_upload_single_txt_document(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Valid TXT upload should route to TextLoader and extract content."""
    pipeline = _build_test_pipeline(tmp_path, monkeypatch)
    uploaded = DummyUploadedFile("notes.txt", b"Meeting Notes Text")

    doc = pipeline.process_upload(uploaded)
    assert doc.source_file == "notes.txt"
    assert doc.document_type == "txt"
    assert doc.pages[0].content == "Meeting Notes Text"


def test_upload_multiple_documents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Processing multiple files should return a list of extracted documents."""
    pipeline = _build_test_pipeline(tmp_path, monkeypatch)
    files = [
        DummyUploadedFile("file1.pdf", b"Content 1"),
        DummyUploadedFile("file2.txt", b"Content 2"),
    ]

    docs = pipeline.process_uploads(files)
    assert len(docs) == 2
    assert docs[0].source_file == "file1.pdf"
    assert docs[1].source_file == "file2.txt"


def test_upload_rejects_unsupported_file_extension(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unsupported file formats (e.g. .docx, .exe) must raise FileValidationError."""
    pipeline = _build_test_pipeline(tmp_path, monkeypatch)
    unsupported = DummyUploadedFile("archive.zip", b"PK...")

    with pytest.raises(FileValidationError, match="Unsupported file type"):
        pipeline.process_upload(unsupported)


def test_upload_rejects_oversized_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Files exceeding max size limit must raise FileValidationError."""
    monkeypatch.setattr(
        "app.ingestion.upload_pipeline.settings",
        SimpleNamespace(
            upload_dir=tmp_path,
            allowed_upload_extensions=("pdf", "txt"),
            max_upload_size_mb=1,  # 1 MB
        ),
    )
    pipeline = UploadPipeline()
    oversized = DummyUploadedFile("large.pdf", b"0" * (1024 * 1024 + 1))

    with pytest.raises(FileValidationError, match="upload limit"):
        pipeline.process_upload(oversized)


@pytest.mark.parametrize(
    "invalid_filename",
    [
        "../etc/passwd",
        "..\\Windows\\System32",
        "",
        "   ",
        ".",
        "..",
        "malicious/../../hack.pdf",
    ],
)
def test_upload_rejects_unsafe_and_traversal_filenames(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invalid_filename: str
) -> None:
    """Path traversal or empty filenames must raise FileValidationError."""
    pipeline = _build_test_pipeline(tmp_path, monkeypatch)
    bad_file = DummyUploadedFile(invalid_filename, b"test content")

    with pytest.raises(FileValidationError):
        pipeline.process_upload(bad_file)
