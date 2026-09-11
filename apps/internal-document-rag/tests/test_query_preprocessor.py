"""Unit tests for query preprocessor normalization and symbol stripping."""

from __future__ import annotations

from app.retrieval.query_preprocessor import QueryPreprocessor


def test_unicode_normalization() -> None:
    # Full-width alphabets normalized to standard ASCII
    assert QueryPreprocessor.preprocess("ｅｎｇｉｎｅｅｒ") == "engineer"
    # Full-width Japanese/ASCII mixture normalized
    assert QueryPreprocessor.preprocess("ＡＢＣ株式会社") == "ABC株式会社"


def test_remove_zero_width_space() -> None:
    # Zero-width spaces removed
    assert QueryPreprocessor.preprocess("Eng\u200bineer") == "Engineer"
    # Other invisible separator boundaries
    assert QueryPreprocessor.preprocess("Hello\u200cWorld") == "HelloWorld"


def test_remove_repeated_symbols() -> None:
    # Repeated symbol sequences collapsed/removed
    raw = "################# What laptop &&&&&&&&&&&&&& model?"
    assert QueryPreprocessor.preprocess(raw) == "What laptop model?"

    # Repeat of single characters (excludes valid single punct)
    assert QueryPreprocessor.preprocess("有給休暇####？？？&&&&") == "有給休暇？"


def test_preserve_valid_punctuation() -> None:
    # Single valid punctuations are preserved
    assert (
        QueryPreprocessor.preprocess("What is the laptop model?")
        == "What is the laptop model?"
    )
    assert (
        QueryPreprocessor.preprocess("Total cost: 200,000 yen.")
        == "Total cost: 200,000 yen."
    )


def test_collapse_whitespace() -> None:
    # Newlines, multiple spaces, tabs collapsed to single space
    raw = "What\n\n\nlaptop\n     model"
    assert QueryPreprocessor.preprocess(raw) == "What laptop model"

    # Trailing/leading spaces trimmed
    assert QueryPreprocessor.preprocess("  trimmed query   ") == "trimmed query"


def test_empty_query() -> None:
    # Query with only repeated symbols collapses to empty string without crash
    assert QueryPreprocessor.preprocess("##########") == ""
    assert QueryPreprocessor.preprocess("") == ""
