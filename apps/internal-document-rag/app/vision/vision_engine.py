from __future__ import annotations

import base64
import logging
from pathlib import Path

import httpx

from app.config import settings
from app.ingestion.exceptions import VisionModelError
from app.vision.caption_cache import ImageCaptionCache

LOGGER = logging.getLogger(__name__)


class VisionEngine:
    """Vision LLM engine generating descriptive captions for extracted images.

    Follows provider router fallback order:
    1. Gemini Vision (google-genai)
    2. Ollama Vision Model (qwen2.5-vl / llava)
    """

    def __init__(self, cache: ImageCaptionCache | None = None) -> None:
        self.cache = cache or ImageCaptionCache()

    @staticmethod
    def _is_fallback_caption(caption: str) -> bool:
        normalized = caption.strip().lower()
        return normalized.startswith(
            (
                "visual diagram/graphic asset",
                "visual image asset",
                "visual diagram analysis",
            )
        )

    @staticmethod
    def _gemini_vision_configured() -> bool:
        api_key = settings.google_api_key
        return bool(
            api_key
            and api_key.strip()
            and api_key.strip() != "your_google_api_key_here"
        )

    def generate_caption(
        self,
        image_path: Path | str,
        image_hash: str | None = None,
        force_refresh: bool = False,
    ) -> str:
        """Generate a detailed textual description for an image file."""
        img_path = Path(image_path)
        if not img_path.exists():
            raise VisionModelError(f"Image file does not exist: {img_path}")

        if image_hash:
            cached_caption = self.cache.get(image_hash)
            if cached_caption:
                if not force_refresh and not self._is_fallback_caption(cached_caption):
                    LOGGER.info(
                        "Retrieved cached caption for image hash %.8s", image_hash
                    )
                    return cached_caption
                LOGGER.info(
                    "Refreshing cached fallback caption for image hash %.8s",
                    image_hash,
                )

        # Attempt Provider Router Order
        caption = ""
        try:
            caption = self._generate_with_gemini(img_path)
        except Exception as gemini_exc:
            LOGGER.warning(
                "Gemini Vision captioning failed for %s: %s. Trying Ollama Vision fallback...",
                img_path.name,
                gemini_exc,
            )
            try:
                caption = self._generate_with_ollama(img_path)
            except Exception as ollama_exc:
                LOGGER.warning(
                    "Ollama Vision fallback failed for %s: %s. Running fallback visual OCR label analysis...",
                    img_path.name,
                    ollama_exc,
                )
                caption = self._generate_fallback_image_ocr_analysis(img_path)

        if image_hash and caption:
            self.cache.set(image_hash, caption)

        return caption

    def _generate_with_gemini(self, image_path: Path) -> str:
        """Generate caption using Google Gemini Vision API."""
        api_key = settings.google_api_key
        if not api_key or api_key.strip() == "your_google_api_key_here":
            raise VisionModelError("Google Gemini API key is not configured.")

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)
            image_bytes = image_path.read_bytes()
            mime_type = (
                "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
            )

            prompt = (
                "Analyze this image from a document in detail. "
                "Describe any diagrams, architecture components, flowcharts, tables, "
                "charts, or text shown in the image. Be clear, concise, and structured."
            )

            response = client.models.generate_content(
                model=settings.gemini_model_name,
                contents=types.Content(
                    parts=[
                        types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                        types.Part.from_text(text=prompt),
                    ]
                ),
            )
            caption = (response.text or "").strip()
            if not caption:
                raise VisionModelError("Gemini returned empty caption.")
            LOGGER.info(
                "Successfully generated Gemini Vision caption for %s (%s chars)",
                image_path.name,
                len(caption),
            )
            return caption
        except Exception as exc:
            raise VisionModelError(f"Gemini Vision API error: {exc}") from exc

    def _generate_with_ollama(self, image_path: Path) -> str:
        """Generate caption using local Ollama Vision model."""
        image_bytes = image_path.read_bytes()
        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        url = f"{settings.ollama_url.rstrip('/')}/api/generate"
        payload = {
            "model": settings.ollama_vision_model,
            "prompt": "Describe this document image, chart, or diagram in detail.",
            "images": [b64_image],
            "stream": False,
        }

        try:
            response = httpx.post(url, json=payload, timeout=settings.ollama_timeout)
            if response.status_code == 200:
                data = response.json()
                caption = data.get("response", "").strip()
                if caption:
                    LOGGER.info(
                        "Successfully generated Ollama Vision caption for %s",
                        image_path.name,
                    )
                    return caption
            raise VisionModelError(
                f"Ollama Vision response status {response.status_code}"
            )
        except Exception as exc:
            raise VisionModelError(f"Ollama Vision request failed: {exc}") from exc

    def _generate_fallback_image_ocr_analysis(self, image_path: Path) -> str:
        """Fallback visual analysis extracting text labels inside image pixels when Vision API is unconfigured."""
        labels: list[str] = []
        try:
            from PIL import Image

            img = Image.open(image_path)
            w, h = img.size

            from app.ocr.ocr_engine import OCREngine

            ocr = OCREngine()
            image_bytes = image_path.read_bytes()
            extracted_text = ocr._try_pytesseract(image_bytes) or ocr._try_easyocr(
                image_bytes
            )
            if extracted_text and extracted_text.strip():
                clean_labels = " | ".join(
                    line.strip() for line in extracted_text.splitlines() if line.strip()
                )
                labels.append(f"Visual Text Labels: {clean_labels}")

            format_str = f"Image File: {image_path.name} ({w}x{h} px, {image_path.suffix.upper()})"
            if labels:
                caption = f"Visual Diagram Analysis ({format_str}):\n" + "\n".join(
                    labels
                )
            else:
                caption = f"Visual Diagram/Graphic Asset ({format_str}). Contains architectural workflow components."
            LOGGER.info(
                "Generated fallback visual OCR analysis for %s (%d chars)",
                image_path.name,
                len(caption),
            )
            return caption
        except Exception as exc:
            LOGGER.warning(
                "Fallback visual analysis failed for %s: %s", image_path.name, exc
            )
            return f"Visual Image Asset ({image_path.name}). Contains diagram/graphic content."


# ---------------------------------------------------------------------------
# Backwards-compatibility alias — VisionService maps to VisionEngine.
# ---------------------------------------------------------------------------
VisionService = VisionEngine
