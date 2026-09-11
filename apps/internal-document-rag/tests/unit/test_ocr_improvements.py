"""Unit tests for OCR Improvements (Multilingual, Cache, Confidence, DPI, Preprocessing, Metadata)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from app.models.schemas import ChunkMetadata, ChunkType, DocumentAsset
from app.ocr.ocr_cache import OCRResultCache
from app.ocr.ocr_preprocessor import preprocess_image_bytes
from app.ocr.ocr_engine import (
    OCREngine,
    OCRService,
    _map_easyocr_langs,
    _map_paddle_lang,
    _map_tesseract_lang,
)


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_ocr_language_mappings():
    """Verify language mapping for PaddleOCR, EasyOCR, and Pytesseract."""
    assert _map_paddle_lang("en") == "en"
    assert _map_paddle_lang("japanese") == "japan"
    assert _map_paddle_lang("chinese") == "ch"
    assert _map_paddle_lang("korean") == "korean"

    assert _map_easyocr_langs("en") == ["en"]
    assert _map_easyocr_langs("japanese") == ["ja", "en"]
    assert _map_easyocr_langs("chinese") == ["ch_sim", "en"]
    assert _map_easyocr_langs("korean") == ["ko", "en"]

    assert _map_tesseract_lang("en") == "eng"
    assert _map_tesseract_lang("japanese") == "jpn"
    assert _map_tesseract_lang("chinese") == "chi_sim"
    assert _map_tesseract_lang("korean") == "kor"


def test_ocr_result_cache_hit_and_miss(temp_dir: Path):
    """Verify OCRResultCache stores and retrieves complete OCR metadata."""
    cache_file = temp_dir / "test_ocr_cache.json"
    cache = OCRResultCache(cache_file=cache_file)

    img_hash = "hash_ocr_12345678"
    assert cache.get(img_hash) is None

    cache.set(
        image_hash=img_hash,
        ocr_text="Scanned invoice text",
        ocr_strategy="PaddleOCR",
        ocr_confidence=0.94,
        elapsed_ms=120.5,
    )

    cached_data = cache.get(img_hash)
    assert cached_data is not None
    assert cached_data["ocr_text"] == "Scanned invoice text"
    assert cached_data["ocr_strategy"] == "PaddleOCR"
    assert cached_data["ocr_confidence"] == 0.94
    assert cached_data["elapsed_ms"] == 120.5

    # Reload from disk
    cache2 = OCRResultCache(cache_file=cache_file)
    reloaded_data = cache2.get(img_hash)
    assert reloaded_data is not None
    assert reloaded_data["ocr_text"] == "Scanned invoice text"


def test_ocr_preprocessor_grayscale_and_contrast():
    """Verify preprocess_image_bytes returns valid PNG image bytes."""
    img = Image.new("RGB", (100, 100), color=(100, 150, 200))
    import io

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    raw_bytes = buf.getvalue()

    processed = preprocess_image_bytes(raw_bytes)
    assert isinstance(processed, bytes)
    assert len(processed) > 0


def test_document_asset_and_chunk_metadata_ocr_fields():
    """Verify OCR metadata fields are preserved in DocumentAsset and ChunkMetadata."""
    asset = DocumentAsset(
        asset_type=ChunkType.OCR,
        page_number=1,
        content="[OCR Text Page 1]\nExtracted text",
        source_file="scanned.pdf",
        document_name="scanned.pdf",
        username="admin",
        ocr_engine="PaddleOCR",
        ocr_confidence=0.95,
        ocr_processing_time_ms=150.0,
    )
    assert asset.ocr_engine == "PaddleOCR"
    assert asset.ocr_confidence == 0.95
    assert asset.ocr_processing_time_ms == 150.0

    meta = ChunkMetadata(
        source_file="scanned.pdf",
        page_number=1,
        chunk_id="c_ocr_1",
        document_type="pdf",
        chunk_type=ChunkType.OCR,
        ocr_engine="PaddleOCR",
        ocr_confidence=0.95,
        ocr_processing_time_ms=150.0,
    )
    chroma_dict = meta.to_chroma_dict()
    assert chroma_dict["ocr_engine"] == "PaddleOCR"
    assert chroma_dict["ocr_confidence"] == 0.95
    assert chroma_dict["ocr_processing_time_ms"] == 150.0


def test_ocr_confidence_threshold_fallback(temp_dir: Path):
    """Verify low confidence PaddleOCR triggers fallback to next engine."""
    cache = OCRResultCache(cache_file=temp_dir / "cache.json")
    ocr_svc = OCRService(ocr_cache=cache)

    with (
        patch.object(
            ocr_svc,
            "_try_paddleocr_with_confidence",
            return_value=("Low confidence garbage", 0.20),
        ),
        patch.object(
            ocr_svc,
            "_try_easyocr",
            return_value="High quality EasyOCR text",
        ),
        patch("app.ocr.ocr_engine.fitz") as mock_fitz,
    ):
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = ""
        mock_pix = MagicMock()
        mock_pix.tobytes.return_value = b"fake_png_bytes"
        mock_page.get_pixmap.return_value = mock_pix
        mock_doc.__len__.return_value = 1
        mock_doc.__getitem__.return_value = mock_page
        mock_fitz.open.return_value = mock_doc

        asset = ocr_svc.process_scanned_page(temp_dir / "scanned.pdf", page_number=1)

        assert asset is not None
        assert "High quality EasyOCR text" in asset.content
        assert asset.ocr_engine == "EasyOCR"
