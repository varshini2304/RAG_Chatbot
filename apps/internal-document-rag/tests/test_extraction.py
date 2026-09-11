from __future__ import annotations

from pathlib import Path

import fitz  # type: ignore[import-untyped]
import pytest

from app.ingestion.exceptions import ExtractionError
from app.ingestion.pdf_loader import PDFLoader
from app.ingestion.text_loader import TextLoader


def test_pdf_loader_extracts_page_text(tmp_path: Path) -> None:
    """PDF extraction should preserve page numbers and page text."""
    pdf_path = tmp_path / "sample.pdf"
    document = fitz.open()
    first_page = document.new_page()
    first_page.insert_text((72, 72), "Page one text")
    second_page = document.new_page()
    second_page.insert_text((72, 72), "Page two text")
    document.save(pdf_path)
    document.close()

    extracted = PDFLoader().extract(pdf_path)

    assert extracted.document_type == "pdf"
    assert extracted.page_count == 2
    assert extracted.pages[0].page_number == 1
    assert extracted.pages[1].page_number == 2
    assert "Page one text" in extracted.pages[0].content
    assert "Page two text" in extracted.pages[1].content


def test_pdf_loader_rejects_pdf_without_text(tmp_path: Path) -> None:
    pdf_path = tmp_path / "blank.pdf"
    document = fitz.open()
    document.new_page()
    document.save(pdf_path)
    document.close()

    extracted = PDFLoader().extract(pdf_path)
    assert extracted.pages[0].content == "[Visual Content / Scanned Page 1]"


def test_pdf_loader_rejects_corrupted_pdf(tmp_path: Path) -> None:
    pdf_path = tmp_path / "corrupted.pdf"
    pdf_path.write_bytes(b"this is not a valid pdf")

    with pytest.raises(ExtractionError, match="Unable to open PDF file"):
        PDFLoader().extract(pdf_path)


def test_pdf_loader_rejects_encrypted_pdf(tmp_path: Path) -> None:
    pdf_path = tmp_path / "encrypted.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Confidential content")

    perm = getattr(fitz, "PDF_PERM_ACCESSIBILITY", 0)
    encrypt_meth = getattr(fitz, "PDF_ENCRYPT_AES_256", 4)
    document.save(
        pdf_path,
        encryption=encrypt_meth,
        owner_pw="owner123",
        user_pw="user123",
        permissions=perm,
    )
    document.close()

    with pytest.raises(ExtractionError, match="encrypted"):
        PDFLoader().extract(pdf_path)


def test_text_loader_extracts_content(tmp_path: Path) -> None:
    txt_path = tmp_path / "readme.txt"
    txt_path.write_text("Hello world.\nSecond line.", encoding="utf-8")

    extracted = TextLoader().extract(txt_path)

    assert extracted.document_type == "txt"
    assert extracted.source_file == "readme.txt"
    assert extracted.page_count == 1
    assert extracted.pages[0].page_number == 1
    assert "Hello world." in extracted.pages[0].content
    assert "Second line." in extracted.pages[0].content


def test_text_loader_extracts_shift_jis_japanese_content(tmp_path: Path) -> None:
    txt_path = tmp_path / "japanese.txt"
    txt_path.write_bytes("これは日本語のテキストです。".encode("cp932"))

    extracted = TextLoader().extract(txt_path)

    assert extracted.document_type == "txt"
    assert extracted.pages[0].content == "これは日本語のテキストです。"


def test_text_loader_rejects_empty_file(tmp_path: Path) -> None:
    txt_path = tmp_path / "empty.txt"
    txt_path.write_text("", encoding="utf-8")

    with pytest.raises(ExtractionError, match="TXT file is empty"):
        TextLoader().extract(txt_path)


def test_text_loader_rejects_undecodable_file(tmp_path: Path) -> None:
    txt_path = tmp_path / "binary.txt"
    txt_path.write_bytes(b"\x80\x81\x82\x83\x84\x85")

    with pytest.raises(ExtractionError, match="Unable to decode TXT file"):
        TextLoader().extract(txt_path)
