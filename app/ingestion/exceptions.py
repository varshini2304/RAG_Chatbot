
from __future__ import annotations


class IngestionError(Exception):
    """Base exception for upload and extraction failures."""


class FileValidationError(IngestionError):
    """Raised when an uploaded file fails validation."""


class ExtractionError(IngestionError):
    """Raised when file text cannot be extracted successfully."""
