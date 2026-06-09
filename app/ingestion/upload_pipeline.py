
from __future__ import annotations

import logging
from pathlib import Path

from streamlit.runtime.uploaded_file_manager import UploadedFile

from app.config import settings
from app.ingestion.exceptions import FileValidationError
from app.ingestion.pdf_loader import PDFLoader
from app.models.schemas import ExtractedPdfDocument

LOGGER = logging.getLogger(__name__)


class UploadPipeline:

    def __init__(self) -> None:
        self._pdf_loader = PDFLoader()

    def process_upload(self, uploaded_file: UploadedFile) -> ExtractedPdfDocument:
        self._validate_upload(uploaded_file)
        saved_path = self._save_upload(uploaded_file)
        return self._pdf_loader.extract(saved_path)

    def process_uploads(
        self, uploaded_files: list[UploadedFile]
    ) -> list[ExtractedPdfDocument]:
        return [self.process_upload(uploaded_file) for uploaded_file in uploaded_files]

    def _validate_upload(self, uploaded_file: UploadedFile) -> None:
        extension = self._get_extension(uploaded_file.name)
        if extension not in settings.allowed_upload_extensions:
            raise FileValidationError("Unsupported file type. Please upload a PDF file.")

        max_size_bytes = settings.max_upload_size_mb * 1024 * 1024
        if uploaded_file.size > max_size_bytes:
            raise FileValidationError(
                f"File exceeds the {settings.max_upload_size_mb} MB upload limit."
            )

    def _save_upload(self, uploaded_file: UploadedFile) -> Path:
        settings.upload_dir.mkdir(parents=True, exist_ok=True)
        destination = settings.upload_dir / uploaded_file.name
        destination.write_bytes(uploaded_file.getbuffer())
        LOGGER.info("Saved uploaded file to %s", destination)
        return destination

    @staticmethod
    def _get_extension(filename: str) -> str:
        return Path(filename).suffix.lower().lstrip(".")
