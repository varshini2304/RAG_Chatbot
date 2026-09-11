from __future__ import annotations

import logging
from pathlib import Path

from app.ingestion.exceptions import ExtractionError
from app.models.schemas import ExtractedPage, ExtractedPdfDocument

LOGGER = logging.getLogger(__name__)

TEXT_ENCODINGS = ("utf-8-sig", "utf-8", "utf-16", "cp932", "shift_jis")


class TextLoader:
    """Extract text content from plain text files using common Unicode/CJK encodings."""

    def extract(self, file_path: Path) -> ExtractedPdfDocument:
        LOGGER.info("Starting TXT extraction for %s", file_path.name)

        text: str | None = None
        for encoding in TEXT_ENCODINGS:
            try:
                text = file_path.read_text(encoding=encoding).strip()
                LOGGER.info("Decoded TXT file %s using %s", file_path.name, encoding)
                break
            except (UnicodeError, ValueError):
                continue

        if text is None:
            raise ExtractionError(f"Unable to decode TXT file: {file_path.name}")

        if not text:
            raise ExtractionError(f"TXT file is empty: {file_path.name}")

        LOGGER.info(
            "Completed TXT extraction for %s (%s characters)",
            file_path.name,
            len(text),
        )
        return ExtractedPdfDocument(
            source_file=file_path.name,
            file_path=file_path,
            document_type="txt",
            pages=[
                ExtractedPage(
                    page_number=1,
                    content=text,
                )
            ],
        )
