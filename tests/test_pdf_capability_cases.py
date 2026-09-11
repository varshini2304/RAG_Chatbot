from __future__ import annotations

from pathlib import Path

import pytest

from app.ingestion.exceptions import ExtractionError
from app.ingestion.pdf_loader import PDFLoader
from sample_docs.generate_extraction_test_pdfs import (
    create_embedded_text_stress_pdf,
    create_image_only_scan_pdf,
    create_mixed_text_and_image_pdf,
    create_password_protected_pdf,
)


def _combined_text(pdf_path: Path) -> str:
    extracted = PDFLoader().extract(pdf_path)
    return "\n".join(page.content for page in extracted.pages)


def test_pdf_loader_handles_embedded_text_stress_cases(tmp_path: Path) -> None:
    pdf_path = tmp_path / "embedded_text_stress.pdf"
    create_embedded_text_stress_pdf(pdf_path)

    text = _combined_text(pdf_path)

    assert "CONFIDENTIAL POLICY UPDATE" in text
    assert "999999999999999999999999" in text
    assert "Hex bytes: 00 FF 7A 10 2B" in text
    assert "TC-002" in text
    assert "LEFT-01" in text
    assert "RIGHT-01" in text
    assert "ROTATED-90" in text


def test_pdf_loader_rejects_image_only_pdf_without_ocr(tmp_path: Path) -> None:
    pdf_path = tmp_path / "image_only_scan.pdf"
    create_image_only_scan_pdf(pdf_path)

    with pytest.raises(ExtractionError, match="No extractable text"):
        PDFLoader().extract(pdf_path)


def test_pdf_loader_extracts_only_embedded_text_from_mixed_pdf(tmp_path: Path) -> None:
    pdf_path = tmp_path / "mixed_text_and_image.pdf"
    create_mixed_text_and_image_pdf(pdf_path)

    text = _combined_text(pdf_path)

    assert "EMBEDDED-TEXT-001" in text
    assert "EMBEDDED-TEXT-003" in text
    assert "IMAGE BLOCK INSIDE MIXED PDF" not in text
    assert "Image-only invoice total" not in text


def test_pdf_loader_rejects_password_protected_pdf(tmp_path: Path) -> None:
    pdf_path = tmp_path / "password_protected.pdf"
    create_password_protected_pdf(pdf_path)

    with pytest.raises(ExtractionError, match="encrypted"):
        PDFLoader().extract(pdf_path)
