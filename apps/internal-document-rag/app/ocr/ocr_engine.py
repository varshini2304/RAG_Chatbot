from __future__ import annotations

import hashlib
import importlib.util
import io
import logging
import threading
import time
from pathlib import Path
from typing import Any, ClassVar

try:
    import fitz  # type: ignore[import-untyped]
except ImportError:
    fitz = None  # type: ignore

try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore

try:
    import pytesseract  # type: ignore[import-untyped]
except ImportError:
    pytesseract = None  # type: ignore

from app.config import settings
from app.ingestion.exceptions import OCRProcessingError
from app.models.schemas import ChunkType, DocumentAsset
from app.ocr.ocr_cache import OCRResultCache
from app.ocr.ocr_preprocessor import preprocess_image_bytes

LOGGER = logging.getLogger(__name__)


def _map_paddle_lang(lang: str) -> str:
    """Map config language to PaddleOCR language code."""
    lang_clean = lang.lower().strip()
    mapping = {
        "en": "en",
        "english": "en",
        "ja": "japan",
        "japan": "japan",
        "japanese": "japan",
        "zh": "ch",
        "ch": "ch",
        "chinese": "ch",
        "ko": "korean",
        "korean": "korean",
    }
    return mapping.get(lang_clean, lang_clean)


def _map_easyocr_langs(lang: str) -> list[str]:
    """Map config language to EasyOCR language codes list."""
    lang_clean = lang.lower().strip()
    mapping = {
        "en": ["en"],
        "english": ["en"],
        "ja": ["ja", "en"],
        "japan": ["ja", "en"],
        "japanese": ["ja", "en"],
        "zh": ["ch_sim", "en"],
        "ch": ["ch_sim", "en"],
        "chinese": ["ch_sim", "en"],
        "ko": ["ko", "en"],
        "korean": ["ko", "en"],
    }
    return mapping.get(lang_clean, [lang_clean])


def _map_tesseract_lang(lang: str) -> str:
    """Map config language to Pytesseract language code."""
    lang_clean = lang.lower().strip()
    mapping = {
        "en": "eng",
        "english": "eng",
        "ja": "jpn",
        "japan": "jpn",
        "japanese": "jpn",
        "zh": "chi_sim",
        "ch": "chi_sim",
        "chinese": "chi_sim",
        "ko": "kor",
        "korean": "kor",
    }
    return mapping.get(lang_clean, lang_clean)


def log_ocr_engine_availability() -> None:
    """Probe and log which OCR engines are importable in the current environment."""
    engines = [
        ("PaddleOCR", "paddleocr"),
        ("EasyOCR", "easyocr"),
        ("Pytesseract", "pytesseract"),
        ("PyMuPDF", "fitz"),
    ]

    available: list[str] = []
    unavailable: list[str] = []
    rows: list[str] = []

    for display_name, package_name in engines:
        found = importlib.util.find_spec(package_name) is not None
        status = "AVAILABLE" if found else "NOT FOUND"
        rows.append(f"  [{status:>9}]  {display_name} ({package_name})")
        (available if found else unavailable).append(display_name)

    report = "\n".join(rows)
    LOGGER.info(
        "OCR ENGINE AVAILABILITY REPORT\n"
        "  Fallback order: PaddleOCR → EasyOCR → Pytesseract → PyMuPDF\n"
        "%s\n"
        "  Ready engines : %s\n"
        "  Missing engines: %s",
        report,
        ", ".join(available) if available else "none",
        ", ".join(unavailable) if unavailable else "none",
    )

    if unavailable:
        LOGGER.warning(
            "OCR engines not installed (will be skipped at runtime): %s. "
            "Run: pip install %s",
            ", ".join(unavailable),
            " ".join(pkg for name, pkg in engines if name in unavailable),
        )


# Report engine availability once when this module is first imported.
log_ocr_engine_availability()


class OCREngine:
    """Optical Character Recognition (OCR) Engine supporting multi-engine fallback."""

    _paddle_lock: threading.Lock = threading.Lock()
    _paddle_instances: ClassVar[dict[str, Any]] = {}

    def __init__(self, ocr_cache: OCRResultCache | None = None) -> None:
        self.ocr_cache = ocr_cache or OCRResultCache()

    def process_scanned_page(
        self,
        pdf_path: Path,
        page_number: int,
        username: str = "default",
        document_name: str | None = None,
    ) -> DocumentAsset | None:
        """Perform OCR recognition on a specific scanned PDF page."""
        doc_name = document_name or pdf_path.name
        LOGGER.info("Performing OCR on page %s of %s", page_number, doc_name)

        if fitz is None:
            LOGGER.warning(
                "PyMuPDF is not installed; skipping OCR for page %s", page_number
            )
            return None

        ocr_text = ""
        ocr_strategy = "none"
        ocr_confidence: float | None = None
        t_start = time.perf_counter()
        is_cached = False
        try:
            document = fitz.open(pdf_path)
            if page_number > len(document):
                document.close()
                return None

            page = document[page_number - 1]
            raw_text = page.get_text("text")
            raw_page_text = str(raw_text or "").strip()
            pix = page.get_pixmap(dpi=settings.ocr_dpi)
            raw_image_bytes = pix.tobytes("png")
            document.close()

            # Preprocess rendered image
            image_bytes = preprocess_image_bytes(raw_image_bytes)
            image_hash = hashlib.sha256(image_bytes).hexdigest()

            # Check OCR Cache first
            if settings.enable_ocr_cache:
                cached_data = self.ocr_cache.get(image_hash)
                if cached_data:
                    ocr_text = cached_data.get("ocr_text", "")
                    ocr_strategy = cached_data.get("ocr_strategy", "cached")
                    ocr_confidence = cached_data.get("ocr_confidence")
                    elapsed_ms = cached_data.get("elapsed_ms", 0.0)
                    is_cached = True
                    LOGGER.info(
                        "OCR CACHE HIT | Page: %s | Doc: %s | Strategy: %s | Hash: %.8s",
                        page_number,
                        doc_name,
                        ocr_strategy,
                        image_hash,
                    )

            if not is_cached:
                LOGGER.info(
                    "OCR CACHE MISS | Page: %s | Doc: %s | Hash: %.8s",
                    page_number,
                    doc_name,
                    image_hash,
                )

                # Strategy 1: PaddleOCR
                ocr_text, ocr_confidence = self._try_paddleocr_with_confidence(
                    image_bytes
                )
                if ocr_text:
                    if (
                        ocr_confidence is not None
                        and ocr_confidence < settings.ocr_confidence_threshold
                    ):
                        LOGGER.warning(
                            "PaddleOCR confidence %.2f is below threshold %.2f on page %s of %s; falling through to next OCR engine",
                            ocr_confidence,
                            settings.ocr_confidence_threshold,
                            page_number,
                            doc_name,
                        )
                        ocr_text = ""
                        ocr_confidence = None
                    else:
                        ocr_strategy = "PaddleOCR"

                # Strategy 2: EasyOCR
                if not ocr_text:
                    ocr_text = self._try_easyocr(image_bytes)
                    if ocr_text:
                        ocr_strategy = "EasyOCR"

                # Strategy 3: Pytesseract
                if not ocr_text:
                    ocr_text = self._try_pytesseract(image_bytes)
                    if ocr_text:
                        ocr_strategy = "Pytesseract"

                # Strategy 4: Fallback render text
                if not ocr_text:
                    ocr_text = raw_page_text
                    if ocr_text:
                        ocr_strategy = "PyMuPDF Fallback"

                elapsed_ms = (time.perf_counter() - t_start) * 1000

                # Cache result if valid text extracted
                if settings.enable_ocr_cache and ocr_text.strip():
                    self.ocr_cache.set(
                        image_hash,
                        ocr_text.strip(),
                        ocr_strategy,
                        ocr_confidence,
                        elapsed_ms,
                    )

        except Exception as exc:
            LOGGER.error(
                "OCR recognition error on page %s of %s: %s", page_number, doc_name, exc
            )
            raise OCRProcessingError(
                f"OCR failed for page {page_number}: {exc}"
            ) from exc

        char_count = len(ocr_text.strip())
        confidence_str = (
            f"{ocr_confidence:.2f}" if ocr_confidence is not None else "N/A"
        )
        LOGGER.info(
            "OCR COMPLETED | Page: %s | Doc: %s | Strategy: %s | "
            "Characters: %d | Confidence: %s | Time: %.1f ms",
            page_number,
            doc_name,
            ocr_strategy,
            char_count,
            confidence_str,
            elapsed_ms,
        )

        if not ocr_text.strip():
            return None

        return DocumentAsset(
            asset_type=ChunkType.OCR,
            page_number=page_number,
            content=f"[OCR Text Page {page_number}]\n{ocr_text.strip()}",
            source_file=pdf_path.name,
            document_name=doc_name,
            username=username,
            ocr_engine=ocr_strategy,
            ocr_confidence=ocr_confidence,
            ocr_processing_time_ms=elapsed_ms,
        )

    def _try_paddleocr_with_confidence(
        self, image_bytes: bytes
    ) -> tuple[str, float | None]:
        """Run PaddleOCR and return (text, mean_confidence) or ("", None) on failure."""
        try:
            from paddleocr import PaddleOCR  # type: ignore[import-untyped]

            paddle_lang = _map_paddle_lang(settings.ocr_language)
            if paddle_lang not in OCREngine._paddle_instances:
                with OCREngine._paddle_lock:
                    if paddle_lang not in OCREngine._paddle_instances:
                        LOGGER.info(
                            "Initialising PaddleOCR singleton for language '%s'...",
                            paddle_lang,
                        )
                        OCREngine._paddle_instances[paddle_lang] = PaddleOCR(
                            use_angle_cls=True, lang=paddle_lang, show_log=False
                        )
                        LOGGER.info(
                            "PaddleOCR singleton for language '%s' ready and cached",
                            paddle_lang,
                        )
            ocr = OCREngine._paddle_instances[paddle_lang]
            result = ocr.ocr(image_bytes, cls=True)
            lines: list[str] = []
            confidences: list[float] = []

            if result:
                for item in result:
                    if not item:
                        continue
                    # Handle PaddleOCR 3.x dict format
                    if isinstance(item, dict):
                        rec_text = (
                            item.get("rec_text")
                            or item.get("transcription")
                            or item.get("text")
                        )
                        rec_score = (
                            item.get("rec_score")
                            or item.get("score")
                            or item.get("confidence")
                        )
                        if isinstance(rec_text, list):
                            for txt in rec_text:
                                if isinstance(txt, str) and txt.strip():
                                    lines.append(txt.strip())
                                elif isinstance(txt, dict):
                                    t = (
                                        txt.get("text")
                                        or txt.get("transcription")
                                        or ""
                                    )
                                    if str(t).strip():
                                        lines.append(str(t).strip())
                        elif isinstance(rec_text, str) and rec_text.strip():
                            lines.append(rec_text.strip())

                        if isinstance(rec_score, list):
                            confidences.extend(
                                [
                                    float(s)
                                    for s in rec_score
                                    if isinstance(s, (int, float))
                                ]
                            )
                        elif isinstance(rec_score, (int, float)):
                            confidences.append(float(rec_score))
                        continue

                    # Handle PaddleOCR 2.x list/tuple format
                    if isinstance(item, (list, tuple)):
                        for line in item:
                            if isinstance(line, dict):
                                txt = (
                                    line.get("rec_text")
                                    or line.get("transcription")
                                    or line.get("text")
                                )
                                sc = (
                                    line.get("rec_score")
                                    or line.get("score")
                                    or line.get("confidence")
                                )
                                if isinstance(txt, str) and txt.strip():
                                    lines.append(txt.strip())
                                if isinstance(sc, (int, float)):
                                    confidences.append(float(sc))
                            elif isinstance(line, (list, tuple)) and len(line) > 1:
                                val = line[1]
                                if isinstance(val, dict):
                                    txt = (
                                        val.get("rec_text")
                                        or val.get("transcription")
                                        or val.get("text")
                                    )
                                    sc = (
                                        val.get("rec_score")
                                        or val.get("score")
                                        or val.get("confidence")
                                    )
                                    if isinstance(txt, str) and txt.strip():
                                        lines.append(txt.strip())
                                    if isinstance(sc, (int, float)):
                                        confidences.append(float(sc))
                                elif isinstance(val, (list, tuple)) and len(val) > 0:
                                    txt = val[0]
                                    if isinstance(txt, str) and txt.strip():
                                        lines.append(txt.strip())
                                    if len(val) > 1 and isinstance(
                                        val[1], (int, float)
                                    ):
                                        confidences.append(float(val[1]))
                                elif isinstance(val, str) and val.strip():
                                    lines.append(val.strip())

            text = "\n".join(lines)
            mean_conf = (sum(confidences) / len(confidences)) if confidences else None
            return text, mean_conf
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("PaddleOCR recognition error: %s", exc)
            return "", None

    def _try_paddleocr(self, image_bytes: bytes) -> str:
        """Compatibility wrapper — returns text only."""
        text, _ = self._try_paddleocr_with_confidence(image_bytes)
        return text

    def _try_easyocr(self, image_bytes: bytes) -> str:
        try:
            import easyocr  # type: ignore[import-untyped]

            langs = _map_easyocr_langs(settings.ocr_language)
            reader = easyocr.Reader(langs)
            results = reader.readtext(image_bytes, detail=0)
            if isinstance(results, dict):
                results = results.get("text") or results.get("transcription") or []
            if isinstance(results, list):
                extracted = []
                for item in results:
                    if isinstance(item, dict):
                        t = item.get("text") or item.get("transcription") or ""
                        if str(t).strip():
                            extracted.append(str(t).strip())
                    elif isinstance(item, (list, tuple)) and len(item) > 0:
                        t = item[0]
                        if str(t).strip():
                            extracted.append(str(t).strip())
                    elif isinstance(item, str) and item.strip():
                        extracted.append(item.strip())
                return "\n".join(extracted)
            elif isinstance(results, str):
                return results.strip()
            return ""
        except Exception:  # noqa: BLE001
            return ""

    def _try_pytesseract(self, image_bytes: bytes) -> str:
        if pytesseract is None or Image is None:
            return ""
        try:
            img = Image.open(io.BytesIO(image_bytes))
            tess_lang = _map_tesseract_lang(settings.ocr_language)
            text = pytesseract.image_to_string(img, lang=tess_lang)
            if isinstance(text, dict):
                extracted = text.get("text") or text.get("transcription") or ""
                if isinstance(extracted, list):
                    return "\n".join(
                        str(item).strip() for item in extracted if str(item).strip()
                    )
                return str(extracted).strip()
            if isinstance(text, list):
                return "\n".join(
                    str(item).strip() for item in text if str(item).strip()
                )
            if isinstance(text, str):
                return text.strip()
            return str(text or "").strip()
        except Exception:  # noqa: BLE001
            return ""


# ---------------------------------------------------------------------------
# Backwards-compatibility alias — OCRService maps to OCREngine.
# ---------------------------------------------------------------------------
OCRService = OCREngine
