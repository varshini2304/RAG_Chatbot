from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

from app.ingestion.exceptions import FileValidationError
from app.ingestion.upload_pipeline import UploadPipeline
from app.models.schemas import ExtractedPage, ExtractedPdfDocument

# =========================================================================
# Fakes
# =========================================================================


if TYPE_CHECKING:
    from app.ingestion.pdf_loader import PDFLoader
    from app.ingestion.text_loader import TextLoader

    _BasePDFLoader = PDFLoader
    _BaseTextLoader = TextLoader
else:
    _BasePDFLoader = object
    _BaseTextLoader = object


class FakeUploadedFile:
    def __init__(self, name: str, content: bytes) -> None:
        self.name = name
        self.size = len(content)
        self._content = content

    def getbuffer(self) -> memoryview:
        return memoryview(self._content)


class FakePDFLoader(_BasePDFLoader):
    def extract(self, file_path: Path) -> ExtractedPdfDocument:
        return ExtractedPdfDocument(
            source_file=file_path.name,
            file_path=file_path,
            pages=[ExtractedPage(page_number=1, content=file_path.read_text())],
        )


class FakeTextLoader(_BaseTextLoader):
    def extract(self, file_path: Path) -> ExtractedPdfDocument:
        return ExtractedPdfDocument(
            source_file=file_path.name,
            file_path=file_path,
            document_type="txt",
            pages=[ExtractedPage(page_number=1, content=file_path.read_text())],
        )


def _make_pipeline(tmp_path: Path, monkeypatch) -> UploadPipeline:
    """Create a pipeline with faked loaders and a tmp upload dir."""
    monkeypatch.setattr(
        "app.ingestion.upload_pipeline.settings",
        SimpleNamespace(
            upload_dir=tmp_path,
            allowed_upload_extensions=("pdf", "txt"),
            max_upload_size_mb=10,
        ),
    )
    pipeline = UploadPipeline()
    pipeline._pdf_loader = FakePDFLoader()
    pipeline._text_loader = FakeTextLoader()
    return pipeline


# =========================================================================
# Happy-path tests
# =========================================================================


def test_upload_pipeline_processes_multiple_uploads(tmp_path, monkeypatch) -> None:
    pipeline = _make_pipeline(tmp_path, monkeypatch)

    documents = pipeline.process_uploads(
        [
            FakeUploadedFile("policy.pdf", b"Policy text"),
            FakeUploadedFile("handbook.pdf", b"Handbook text"),
        ]
    )

    assert [document.source_file for document in documents] == [
        "policy.pdf",
        "handbook.pdf",
    ]
    assert [document.pages[0].content for document in documents] == [
        "Policy text",
        "Handbook text",
    ]


def test_upload_pipeline_routes_txt_to_text_loader(tmp_path, monkeypatch) -> None:
    """A .txt upload should be routed to TextLoader, not PDFLoader."""
    pipeline = _make_pipeline(tmp_path, monkeypatch)

    doc = pipeline.process_upload(
        FakeUploadedFile("notes.txt", b"Meeting notes content")
    )

    assert doc.source_file == "notes.txt"
    assert doc.document_type == "txt"
    assert doc.pages[0].content == "Meeting notes content"


def test_upload_pipeline_routes_pdf_and_txt_together(tmp_path, monkeypatch) -> None:
    """Mixed PDF and TXT uploads should each route to the correct loader."""
    pipeline = _make_pipeline(tmp_path, monkeypatch)

    documents = pipeline.process_uploads(
        [
            FakeUploadedFile("report.pdf", b"PDF content"),
            FakeUploadedFile("readme.txt", b"TXT content"),
        ]
    )

    assert documents[0].document_type == "pdf"
    assert documents[1].document_type == "txt"


# =========================================================================
# Validation error tests
# =========================================================================


def test_upload_pipeline_rejects_unsupported_extension(tmp_path, monkeypatch) -> None:
    """Uploading an unsupported file type should raise FileValidationError."""
    pipeline = _make_pipeline(tmp_path, monkeypatch)

    with pytest.raises(FileValidationError, match="Unsupported file type"):
        pipeline.process_upload(FakeUploadedFile("document.docx", b"Docx content"))


def test_upload_pipeline_rejects_oversized_file(tmp_path, monkeypatch) -> None:
    """Uploading a file exceeding the size limit should raise FileValidationError."""
    monkeypatch.setattr(
        "app.ingestion.upload_pipeline.settings",
        SimpleNamespace(
            upload_dir=tmp_path,
            allowed_upload_extensions=("pdf", "txt"),
            max_upload_size_mb=1,  # 1 MB limit
        ),
    )
    pipeline = UploadPipeline()

    # Create a file slightly over 1 MB
    oversized_content = b"x" * (1 * 1024 * 1024 + 1)

    with pytest.raises(FileValidationError, match="upload limit"):
        pipeline.process_upload(FakeUploadedFile("big.pdf", oversized_content))


@pytest.mark.parametrize(
    "bad_filename",
    [
        "../../evil.txt",
        "/etc/passwd",
        "C:\\Windows\\system32\\cmd.exe",
        "........",
        "",
        "   ",
        ".",
        "..",
        "a/../../b.pdf",
    ],
)
def test_upload_pipeline_rejects_unsafe_filenames(
    tmp_path, monkeypatch, bad_filename
) -> None:
    """Unsafe, traversal, empty, or path-escaping filenames must raise FileValidationError."""
    pipeline = _make_pipeline(tmp_path, monkeypatch)
    with pytest.raises(FileValidationError):
        pipeline.process_upload(FakeUploadedFile(bad_filename, b"content"))
