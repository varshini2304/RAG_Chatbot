from __future__ import annotations

import json
import logging
from pathlib import Path

from app.config import settings

LOGGER = logging.getLogger(__name__)


class ImageCaptionCache:
    """Persistent SHA-256 hash-based cache for generated image captions."""

    def __init__(self, cache_file: Path | None = None) -> None:
        self.cache_file = cache_file or (
            settings.data_dir / "cache" / "image_captions.json"
        )
        self._cache: dict[str, str] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        if self.cache_file.exists():
            try:
                data = json.loads(self.cache_file.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self._cache = data
                    LOGGER.info(
                        "Loaded %s cached image captions from %s",
                        len(self._cache),
                        self.cache_file.name,
                    )
            except Exception as exc:
                LOGGER.warning("Failed to load image caption cache: %s", exc)

    def _save_cache(self) -> None:
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            self.cache_file.write_text(
                json.dumps(self._cache, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as exc:
            LOGGER.warning("Failed to save image caption cache: %s", exc)

    def get(self, image_hash: str) -> str | None:
        return self._cache.get(image_hash)

    def set(self, image_hash: str, caption: str) -> None:
        self._cache[image_hash] = caption
        self._save_cache()

    def delete(self, image_hash: str) -> None:
        if image_hash in self._cache:
            self._cache.pop(image_hash, None)
            self._save_cache()
