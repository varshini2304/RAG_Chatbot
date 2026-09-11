from __future__ import annotations

import io
import logging

try:
    from PIL import Image, ImageEnhance, ImageOps
except ImportError:
    Image = None  # type: ignore
    ImageEnhance = None  # type: ignore
    ImageOps = None  # type: ignore

from app.config import settings

LOGGER = logging.getLogger(__name__)


def preprocess_image_bytes(image_bytes: bytes) -> bytes:
 
    if not settings.enable_ocr_preprocessing or Image is None:
        return image_bytes

    try:
        img = Image.open(io.BytesIO(image_bytes))

        # Convert to Grayscale
        if img.mode != "L":
            img = ImageOps.grayscale(img)

        # Enhance Contrast (1.5 factor)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        processed_bytes = buf.getvalue()
        LOGGER.debug(
            "Preprocessed image bytes for OCR (%d -> %d bytes)",
            len(image_bytes),
            len(processed_bytes),
        )
        return processed_bytes
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("Image preprocessing for OCR failed, using raw bytes: %s", exc)
        return image_bytes
