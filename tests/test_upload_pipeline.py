from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from app.ingestion.upload_pipeline import UploadPipeline
from app.models.schemas import ExtractedPage, ExtractedPdfDocument


class FakeUploadedFile:
    def __init__(self, name: str, content: bytes) -> None:
        self.name = name
        self.size = len(content)
        self._content = content

    def getbuffer(self) -> memoryview:
        return memoryview(self._content)


class FakePDFLoader:
    def extract(self, file_path: Path) -> ExtractedPdfDocument:
        return ExtractedPdfDocument(
            source_file=file_path.name,
            file_path=file_path,
            pages=[ExtractedPage(page_number=1, content=file_path.read_text())],
        )


def test_upload_pipeline_processes_multiple_uploads(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.ingestion.upload_pipeline.settings",
        SimpleNamespace(
            upload_dir=tmp_path,
            allowed_upload_extensions=("pdf",),
            max_upload_size_mb=10,
        ),
    )
    pipeline = UploadPipeline()
    pipeline._pdf_loader = FakePDFLoader()

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
