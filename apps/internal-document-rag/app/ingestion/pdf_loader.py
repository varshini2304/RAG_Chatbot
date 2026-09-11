from __future__ import annotations

import logging
from pathlib import Path

try:
    import fitz  # type: ignore[import-untyped]
except ImportError:
    fitz = None  # type: ignore

from app.ingestion.exceptions import ExtractionError
from app.models.schemas import ExtractedPage, ExtractedPdfDocument

LOGGER = logging.getLogger(__name__)


class PDFLoader:
    """Extract page-by-page text from PDF documents using PyMuPDF."""

    def extract(self, file_path: Path) -> ExtractedPdfDocument:
        """Open a PDF and return its extracted text page by page."""
        LOGGER.info("Starting PDF extraction for %s", file_path.name)

        if fitz is None:
            raise ExtractionError("PyMuPDF (fitz) module is not installed.")

        try:
            document = fitz.open(file_path)
        except (RuntimeError, ValueError) as exc:
            LOGGER.exception("Failed to open PDF file %s", file_path.name)
            raise ExtractionError(f"Unable to open PDF file: {file_path.name}") from exc

        try:
            if document.needs_pass:
                LOGGER.warning("Encrypted PDF detected: %s", file_path.name)
                raise ExtractionError(
                    f"PDF file is encrypted and cannot be processed: {file_path.name}"
                )

            pages: list[ExtractedPage] = []
            for page_idx in range(len(document)):
                page_index = page_idx + 1
                page = document[page_idx]
                raw_text = page.get_text("text")
                page_text = str(raw_text or "").strip()
                if not page_text:
                    page_text = f"[Visual Content / Scanned Page {page_index}]"

                pages.append(
                    ExtractedPage(
                        page_number=page_index,
                        content=page_text,
                    )
                )

            if not pages:
                LOGGER.warning("No extractable text found in PDF %s", file_path.name)
                raise ExtractionError(
                    f"No extractable text was found in PDF file: {file_path.name}"
                )

            LOGGER.info(
                "Completed PDF extraction for %s with %s pages",
                file_path.name,
                len(pages),
            )
            return ExtractedPdfDocument(
                source_file=file_path.name,
                file_path=file_path,
                document_type="pdf",
                pages=pages,
            )
        finally:
            document.close()
