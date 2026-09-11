"""Language detection utility using lingua-language-detector."""

import logging
from typing import Any

LOGGER = logging.getLogger(__name__)

Language: Any = None
LanguageDetectorBuilder: Any = None
_DETECTOR: Any = None

try:
    from lingua import Language, LanguageDetectorBuilder

    # Build detector specifically for English and Japanese for high accuracy
    _DETECTOR = LanguageDetectorBuilder.from_languages(
        Language.ENGLISH, Language.JAPANESE
    ).build()
except ImportError:
    LOGGER.warning(
        "lingua-language-detector is not installed. Falling back to default English detection."
    )
    _DETECTOR = None
except Exception:
    LOGGER.exception("Failed to initialize Lingua language detector")
    _DETECTOR = None


def detect_language(text: str) -> str:
    """Detect the primary language of a query.

    Returns:
        "ja" for Japanese, "en" for English or as a fallback for others.
    """
    if not text or not text.strip():
        return "en"

    if _DETECTOR is None:
        return "en"

    try:
        lang = _DETECTOR.detect_language_of(text.strip())
        if lang == Language.JAPANESE:
            return "ja"
        elif lang == Language.ENGLISH:
            return "en"
        return "en"
    except Exception as exc:
        LOGGER.error("Language detection failed: %s. Defaulting to 'en'.", exc)
        return "en"
