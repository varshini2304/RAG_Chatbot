from __future__ import annotations


class IngestionError(Exception):
    """Base exception for upload and extraction failures."""


class FileValidationError(IngestionError):
    """Raised when an uploaded file fails validation."""


class ExtractionError(IngestionError):
    """Raised when file text cannot be extracted successfully."""


class ChunkingError(IngestionError):
    """Raised when extracted document text cannot be chunked successfully."""


class MetadataValidationError(ChunkingError):
    """Raised when generated chunk metadata is missing or invalid."""


class ImageExtractionError(IngestionError):
    """Raised when extracting images from PDF document fails."""


class VisionModelError(IngestionError):
    """Raised when vision model caption generation fails."""


class OCRProcessingError(IngestionError):
    """Raised when OCR recognition on scanned pages fails."""


class TableExtractionError(IngestionError):
    """Raised when extracting tables from document fails."""
