
from __future__ import annotations

import logging
from pathlib import Path

import fitz

from app.ingestion.exceptions import ExtractionError
from app.models.schemas import ExtractedPage, ExtractedPdfDocument

LOGGER = logging.getLogger(__name__)


class PDFLoader:
    

    def extract(self, file_path: Path) -> ExtractedPdfDocument:
        LOGGER.info("Starting PDF extraction for %s", file_path.name)

        try:
            document = fitz.open(file_path)
        except (RuntimeError, ValueError) as exc:
            raise ExtractionError(f"Unable to open PDF file: {file_path.name}") from exc

        try:
            if document.needs_pass:
                raise ExtractionError(
                    f"PDF file is encrypted and cannot be processed: {file_path.name}"
                )

            pages: list[ExtractedPage] = []
            for page_index, page in enumerate(document, start=1):
                page_text = page.get_text("text").strip()
                if not page_text:
                    continue

                pages.append(
                    ExtractedPage(
                        page_number=page_index,
                        content=page_text,
                    )
                )

            if not pages:
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
