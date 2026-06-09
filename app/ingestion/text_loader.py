
from __future__ import annotations

import logging
from pathlib import Path

from app.ingestion.exceptions import ExtractionError
from app.models.schemas import ExtractedPage, ExtractedPdfDocument

LOGGER = logging.getLogger(__name__)


class TextLoader:
    def extract(self, file_path: Path) -> ExtractedPdfDocument:
        LOGGER.info("Starting TXT extraction for %s", file_path.name)

        try:
            text = file_path.read_text(encoding="utf-8").strip()
        except UnicodeDecodeError as exc:
            raise ExtractionError(f"Unable to decode TXT file: {file_path.name}") from exc

        if not text:
            raise ExtractionError(f"TXT file is empty: {file_path.name}")

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
