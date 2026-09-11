"""
app/ocr/ocr_service.py — Backwards-compatibility shim.

All classes and symbols have moved to app.ocr.ocr_engine.
This module re-exports everything so that existing imports continue to work
without modification during and after the rename migration.
"""

from __future__ import annotations

from app.ocr.ocr_engine import (  # noqa: F401
    Image,
    OCREngine,
    OCREngine as OCRService,
    _map_easyocr_langs,
    _map_paddle_lang,
    _map_tesseract_lang,
    fitz,
    log_ocr_engine_availability,
    preprocess_image_bytes,
    pytesseract,
)

__all__ = [
    "Image",
    "OCREngine",
    "OCRService",
    "fitz",
    "log_ocr_engine_availability",
    "preprocess_image_bytes",
    "pytesseract",
]
