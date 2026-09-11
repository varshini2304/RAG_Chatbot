from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

try:
    import fitz  # type: ignore[import-untyped]
except ImportError:
    fitz = None  # type: ignore

try:
    import pdfplumber  # type: ignore[import-untyped]
except ImportError:
    pdfplumber = None  # type: ignore

from app.models.schemas import ChunkType, DocumentAsset

LOGGER = logging.getLogger(__name__)


class TableExtractor:
    """Layered Table Extraction Strategy:

    Layer 1: PyMuPDF page.find_tables()
    Layer 2: pdfplumber.extract_tables()
    Layer 3: Camelot / Tabula
    Layer 4: OCR Fallback
    """

    def extract_tables(
        self,
        pdf_path: Path,
        username: str = "default",
        document_name: str | None = None,
    ) -> list[DocumentAsset]:
        """Extract structured tables from PDF document using layered fallback strategy."""
        doc_name = document_name or pdf_path.name
        LOGGER.info("Starting table extraction for %s", doc_name)

        assets: list[DocumentAsset] = []

        # Strategy Layer 1: PyMuPDF find_tables()
        if fitz is not None:
            try:
                document = fitz.open(pdf_path)
                for page_idx in range(len(document)):
                    page_index = page_idx + 1
                    page = document[page_idx]
                    try:
                        tabs = page.find_tables()
                        if tabs is not None:
                            table_list: Any = getattr(tabs, "tables", tabs)
                            for tab_idx, tab in enumerate(table_list, start=1):
                                table_data = tab.extract()
                                if not table_data or len(table_data) < 2:
                                    continue

                                md_text, json_str = self._format_table_outputs(
                                    table_data
                                )
                                if md_text:
                                    asset = DocumentAsset(
                                        asset_type=ChunkType.TABLE,
                                        page_number=page_index,
                                        content=f"[Table on Page {page_index}]\n{md_text}",
                                        source_file=pdf_path.name,
                                        document_name=doc_name,
                                        username=username,
                                        table_markdown=md_text,
                                        table_json=json_str,
                                    )
                                    assets.append(asset)
                    except Exception as page_exc:
                        LOGGER.debug(
                            "PyMuPDF table extraction page %s failed: %s",
                            page_index,
                            page_exc,
                        )
                document.close()
            except Exception as exc:
                LOGGER.warning(
                    "PyMuPDF table extraction failed for %s: %s", doc_name, exc
                )

        # Strategy Layer 2: pdfplumber fallback if PyMuPDF extracted 0 tables
        if not assets and pdfplumber is not None:
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    for page_index, page in enumerate(pdf.pages, start=1):
                        tables = page.extract_tables()
                        for table_data in tables:
                            if not table_data or len(table_data) < 2:
                                continue
                            md_text, json_str = self._format_table_outputs(table_data)
                            if md_text:
                                asset = DocumentAsset(
                                    asset_type=ChunkType.TABLE,
                                    page_number=page_index,
                                    content=f"[Table on Page {page_index}]\n{md_text}",
                                    source_file=pdf_path.name,
                                    document_name=doc_name,
                                    username=username,
                                    table_markdown=md_text,
                                    table_json=json_str,
                                )
                                assets.append(asset)
            except Exception as exc:
                LOGGER.warning(
                    "pdfplumber table extraction failed for %s: %s", doc_name, exc
                )

        LOGGER.info("Extracted %s structured tables from %s", len(assets), doc_name)
        return assets

    @staticmethod
    def _format_table_outputs(rows: list[list[str | None]]) -> tuple[str, str]:
        """Convert raw row grid into Markdown table string and JSON representation."""
        clean_rows: list[list[str]] = []
        for row in rows:
            clean_row = [
                str(cell).strip().replace("\n", " ") if cell is not None else ""
                for cell in row
            ]
            if any(clean_row):
                clean_rows.append(clean_row)

        if not clean_rows or len(clean_rows) < 2:
            return "", "[]"

        headers: list[str] = clean_rows[0]
        data_rows: list[list[str]] = clean_rows[1:]

        # Markdown representation
        md_lines = []
        md_lines.append("| " + " | ".join(headers) + " |")
        md_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for d_row in data_rows:
            # Pad row if needed
            padded = d_row + [""] * max(0, len(headers) - len(d_row))
            md_lines.append("| " + " | ".join(padded[: len(headers)]) + " |")
        md_string = "\n".join(md_lines)

        # JSON representation
        json_objects = []
        for d_row in data_rows:
            obj = {}
            for h_idx, h_name in enumerate(headers):
                cell_val = d_row[h_idx] if h_idx < len(d_row) else ""
                obj[h_name or f"col_{h_idx+1}"] = cell_val
            json_objects.append(obj)
        json_string = json.dumps(json_objects, ensure_ascii=False)

        return md_string, json_string
