from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Protocol

from app.config import settings
from app.ingestion.exceptions import FileValidationError
from app.ingestion.pdf_loader import PDFLoader
from app.ingestion.text_loader import TextLoader
from app.models.schemas import ExtractedPdfDocument

LOGGER = logging.getLogger(__name__)


class UploadedFileProtocol(Protocol):
    """Protocol defining the interface required for uploaded document files."""

    name: str
    size: int

    def getbuffer(self) -> memoryview: ...


class UploadPipeline:
    """Validate, save, and extract uploaded documents."""

    def __init__(self, upload_dir: Path | None = None) -> None:
        self._pdf_loader = PDFLoader()
        self._text_loader = TextLoader()
        self.upload_dir = upload_dir or settings.upload_dir

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent directory traversal and resolve outside upload directory."""
        if not filename or not filename.strip():
            raise FileValidationError("Filename must not be empty.")

        # Check for relative path separators or directory traversal
        normalized = filename.replace("\\", "/")
        if (
            normalized in (".", "..")
            or "/../" in normalized
            or normalized.startswith("../")
            or normalized.endswith("/..")
        ):
            raise FileValidationError(
                "Directory traversal attempt detected in filename."
            )

        sanitized_name = Path(filename).name
        if not sanitized_name or sanitized_name in (".", ".."):
            raise FileValidationError(
                "Invalid filename: must not resolve to empty, '.' or '..'."
            )

        try:
            # Absolute paths of directories
            upload_dir_abs = self.upload_dir.resolve()
            dest_path_abs = (self.upload_dir / sanitized_name).resolve()

            # Verify that dest_path_abs resolves inside upload_dir_abs
            if os.path.commonpath([upload_dir_abs, dest_path_abs]) != str(
                upload_dir_abs
            ):
                raise FileValidationError(
                    "Filename resolves outside the upload directory."
                )
        except Exception as exc:
            if isinstance(exc, FileValidationError):
                raise
            raise FileValidationError(f"Filename resolution failed: {exc}")

        return sanitized_name

    def process_upload(
        self, uploaded_file: UploadedFileProtocol
    ) -> ExtractedPdfDocument:
        """Validate an uploaded file, save it locally, and extract its text."""
        sanitized_name = self._sanitize_filename(uploaded_file.name)
        self._validate_upload(uploaded_file, sanitized_name)
        saved_path = self._save_upload(uploaded_file, sanitized_name)
        return self._extract(saved_path)

    def process_uploads(
        self, uploaded_files: list[UploadedFileProtocol]
    ) -> list[ExtractedPdfDocument]:
        """Process multiple uploads and return extracted documents in order."""
        return [self.process_upload(uploaded_file) for uploaded_file in uploaded_files]

    def _extract(self, file_path: Path) -> ExtractedPdfDocument:
        """Route extraction to the correct loader based on file extension."""
        extension = file_path.suffix.lower().lstrip(".")
        if extension == "txt":
            return self._text_loader.extract(file_path)
        return self._pdf_loader.extract(file_path)

    def _validate_upload(
        self, uploaded_file: UploadedFileProtocol, sanitized_name: str
    ) -> None:
        LOGGER.info("Validating uploaded file %s", sanitized_name)
        extension = self._get_extension(sanitized_name)
        if extension not in settings.allowed_upload_extensions:
            allowed = ", ".join(
                ext.upper() for ext in settings.allowed_upload_extensions
            )
            LOGGER.warning(
                "Rejected upload %s due to unsupported extension: %s",
                sanitized_name,
                extension,
            )
            raise FileValidationError(
                f"Unsupported file type. Allowed types: {allowed}."
            )

        max_size_bytes = settings.max_upload_size_mb * 1024 * 1024
        if uploaded_file.size > max_size_bytes:
            LOGGER.warning(
                "Rejected upload %s because size %s bytes exceeds limit %s bytes",
                sanitized_name,
                uploaded_file.size,
                max_size_bytes,
            )
            raise FileValidationError(
                f"File exceeds the {settings.max_upload_size_mb} MB upload limit."
            )

    def _save_upload(
        self, uploaded_file: UploadedFileProtocol, sanitized_name: str
    ) -> Path:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        destination = self.upload_dir / sanitized_name
        destination.write_bytes(uploaded_file.getbuffer())
        LOGGER.info("Saved uploaded file %s to %s", sanitized_name, destination)
        return destination

    @staticmethod
    def _get_extension(filename: str) -> str:
        return Path(filename).suffix.lower().lstrip(".")
