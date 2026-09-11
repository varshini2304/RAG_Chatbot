from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.config import settings

LOGGER = logging.getLogger(__name__)


class OCRResultCache:
    """Persistent SHA-256 hash-based cache for OCR recognition results."""

    def __init__(self, cache_file: Path | None = None) -> None:
        self.cache_file = cache_file or (
            settings.data_dir / "cache" / "ocr_results.json"
        )
        self._cache: dict[str, dict[str, Any]] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        if self.cache_file.exists():
            try:
                data = json.loads(self.cache_file.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self._cache = data
                    LOGGER.info(
                        "Loaded %s cached OCR results from %s",
                        len(self._cache),
                        self.cache_file.name,
                    )
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("Failed to load OCR result cache: %s", exc)

    def _save_cache(self) -> None:
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            self.cache_file.write_text(
                json.dumps(self._cache, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Failed to save OCR result cache: %s", exc)

    def get(self, image_hash: str) -> dict[str, Any] | None:
        return self._cache.get(image_hash)

    def set(
        self,
        image_hash: str,
        ocr_text: str,
        ocr_strategy: str,
        ocr_confidence: float | None,
        elapsed_ms: float,
    ) -> None:
        self._cache[image_hash] = {
            "ocr_text": ocr_text,
            "ocr_strategy": ocr_strategy,
            "ocr_confidence": ocr_confidence,
            "elapsed_ms": elapsed_ms,
        }
        self._save_cache()

    def delete(self, image_hash: str) -> None:
        if image_hash in self._cache:
            self._cache.pop(image_hash, None)
            self._save_cache()
