
from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from app.ingestion.exceptions import ExtractionError
from app.ingestion.pdf_loader import PDFLoader
from app.ingestion.text_loader import TextLoader


def test_pdf_loader_extracts_page_text(tmp_path: Path) -> None:
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
    assert extracted.pages[0].metadata.page_number == 1
    assert extracted.pages[1].metadata.page_number == 2
    assert "Page one text" in extracted.pages[0].content
    assert "Page two text" in extracted.pages[1].content


def test_pdf_loader_rejects_pdf_without_text(tmp_path: Path) -> None:
    pdf_path = tmp_path / "blank.pdf"
    document = fitz.open()
    document.new_page()
    document.save(pdf_path)
    document.close()

    with pytest.raises(ExtractionError, match="No extractable text"):
        PDFLoader().extract(pdf_path)


def test_text_loader_extracts_txt_file(tmp_path: Path) -> None:
    text_path = tmp_path / "notes.txt"
    text_path.write_text("Internal policy update", encoding="utf-8")

    extracted = TextLoader().extract(text_path)

    assert extracted.document_type == "txt"
    assert extracted.page_count == 1
    assert extracted.pages[0].metadata.page_number == 1
    assert extracted.pages[0].content == "Internal policy update"


def test_text_loader_rejects_empty_txt_file(tmp_path: Path) -> None:
    text_path = tmp_path / "empty.txt"
    text_path.write_text("", encoding="utf-8")

    with pytest.raises(ExtractionError, match="TXT file is empty"):
        TextLoader().extract(text_path)

#if any other extraction tests are needed, they can be added here so that the image as well as other file types can be tested for extraction.

#i'm changing the commit deatils and also making it show my name instead