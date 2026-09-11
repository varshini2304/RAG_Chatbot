"""Preprocessor for cleaning and normalizing user search queries."""

from __future__ import annotations

import re
import unicodedata


class QueryPreprocessor:

    @staticmethod
    def preprocess(query: str) -> str:

        return QueryPreprocessor.normalize(query)

    @staticmethod
    def normalize(query: str) -> str:

        if not query:
            return ""

        normalized = unicodedata.normalize("NFKC", query)

        normalized = normalized.replace("\xa0", " ").replace("\u202f", " ")
        normalized = re.sub(
            r"[\u200b\u200c\u200d\u200e\u200f\u2028\u2029\u2060\ufeff]",
            "",
            normalized,
        )


        normalized = re.sub(r"([^\w\s\?.,:？。、：]|_){2,}", "", normalized)
        normalized = re.sub(r"\?{2,}", "？", normalized)

        # 4. Collapse consecutive whitespace
        normalized = re.sub(r"\s+", " ", normalized)

        # 5. Trim leading/trailing whitespace
        return normalized.strip()
