"""
app/audio/alignment.py — Word-Level Timestamp Alignment & ASR Error Rate (WER/CER) Evaluator

Implements:
1. TimestampAlignmentEvaluator: Compares Faster-Whisper word timestamps against verified ground truth.
2. WERCEREvaluator: Calculates Word Error Rate and Character Error Rate via dynamic programming Levenshtein distance.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, ClassVar

from app.audio.asr_engine import TranscriptionResult, WordTimestamp


@dataclass(frozen=True)
class AlignmentAnnotation:
    """Ground truth annotation for a word or phrase."""

    phrase: str
    expected_start: float
    expected_end: float


@dataclass(frozen=True)
class PhraseAlignmentResult:
    """Evaluation result for a single ground truth phrase."""

    phrase: str
    expected_start: float
    expected_end: float
    actual_start: float | None
    actual_end: float | None
    start_error_sec: float | None
    end_error_sec: float | None
    within_tolerance: bool
    status: str
    note: str = ""


@dataclass(frozen=True)
class AlignmentEvaluationReport:
    """Summary metrics of timestamp alignment against ground truth."""

    language: str
    total_annotations: int
    matched_count: int
    within_tolerance_count: int
    accuracy_pct: float
    mean_start_error_sec: float | None
    mean_end_error_sec: float | None
    tolerance_sec: float
    phrase_results: list[PhraseAlignmentResult]


class TimestampAlignmentEvaluator:
    """
    Evaluates word-level timestamps produced by Faster-Whisper against
    human-annotated ground truth.
    """

    DEFAULT_TOLERANCE_SEC: ClassVar[float] = 0.5

    # Authoritative R&D Ground Truth Annotations from Row 06
    GROUND_TRUTH_ANNOTATIONS: ClassVar[dict[str, list[dict[str, Any]]]] = {
        "test_instructional_normal.mp4": [
            {"phrase": "Today", "expected_start": 0.00, "expected_end": 0.35},
            {"phrase": "talk", "expected_start": 0.65, "expected_end": 0.90},
            {"phrase": "basic", "expected_start": 0.95, "expected_end": 1.25},
            {"phrase": "mill", "expected_start": 1.30, "expected_end": 1.55},
            {"phrase": "safety", "expected_start": 1.60, "expected_end": 2.05},
            {"phrase": "and", "expected_start": 2.10, "expected_end": 2.25},
            {"phrase": "operation", "expected_start": 2.30, "expected_end": 2.85},
        ],
        "const_01.mp4": [
            {"phrase": "こんにちは", "expected_start": 11.85, "expected_end": 12.20},
            {"phrase": "それでは", "expected_start": 13.65, "expected_end": 14.15},
        ],
    }

    def __init__(self, tolerance_sec: float | None = None):
        self.tolerance_sec = tolerance_sec or self.DEFAULT_TOLERANCE_SEC

    @staticmethod
    def _normalize(text: str) -> str:
        """Removes punctuation and normalizes casing for phonetic match."""
        return re.sub(r"[^\w\s]", "", text).lower().strip()

    def find_phrase_timing(
        self,
        phrase: str,
        words: list[WordTimestamp],
        segments: list[Any],
    ) -> tuple[float | None, float | None]:
        """
        Locates the start and end timestamp of a target phrase in transcribed words.
        Falls back to segment-level matching if individual word timestamp is unindexed.
        """
        norm_phrase = self._normalize(phrase)
        if not norm_phrase:
            return None, None

        # 1. Word-level search
        for w in words:
            norm_w = self._normalize(w.word)
            if norm_phrase in norm_w or norm_w in norm_phrase:
                return w.start, w.end

        # 2. Segment-level fallback search
        for s in segments:
            norm_seg = self._normalize(s.text)
            if norm_phrase in norm_seg:
                return s.start, s.end

        return None, None

    def evaluate(
        self,
        transcription: TranscriptionResult,
        annotations: list[AlignmentAnnotation] | list[dict[str, Any]],
        language: str = "en",
    ) -> AlignmentEvaluationReport:
        """
        Evaluates transcription timestamps against provided ground-truth annotations.
        """
        phrase_results: list[PhraseAlignmentResult] = []
        start_errors: list[float] = []
        end_errors: list[float] = []

        for item in annotations:
            phrase = item.phrase if isinstance(item, AlignmentAnnotation) else item["phrase"]
            exp_start = (
                item.expected_start
                if isinstance(item, AlignmentAnnotation)
                else item["expected_start"]
            )
            exp_end = (
                item.expected_end
                if isinstance(item, AlignmentAnnotation)
                else item["expected_end"]
            )

            actual_start, actual_end = self.find_phrase_timing(
                phrase, transcription.words, transcription.segments
            )

            if actual_start is None:
                phrase_results.append(
                    PhraseAlignmentResult(
                        phrase=phrase,
                        expected_start=exp_start,
                        expected_end=exp_end,
                        actual_start=None,
                        actual_end=None,
                        start_error_sec=None,
                        end_error_sec=None,
                        within_tolerance=False,
                        status="NOT_FOUND",
                        note="Phrase not found in transcription",
                    )
                )
            else:
                act_end = actual_end or actual_start
                start_err = round(abs(actual_start - exp_start), 4)
                end_err = round(abs(act_end - exp_end), 4)
                within = (start_err <= self.tolerance_sec) and (end_err <= self.tolerance_sec)

                start_errors.append(start_err)
                end_errors.append(end_err)

                phrase_results.append(
                    PhraseAlignmentResult(
                        phrase=phrase,
                        expected_start=exp_start,
                        expected_end=exp_end,
                        actual_start=actual_start,
                        actual_end=act_end,
                        start_error_sec=start_err,
                        end_error_sec=end_err,
                        within_tolerance=within,
                        status="PASS" if within else "EXCEEDS_TOLERANCE",
                        note="",
                    )
                )

        total = len(annotations)
        within_count = sum(1 for r in phrase_results if r.within_tolerance)
        matched_count = sum(1 for r in phrase_results if r.actual_start is not None)
        accuracy_pct = round((within_count / total * 100.0), 2) if total > 0 else 0.0

        mean_start = round(sum(start_errors) / len(start_errors), 4) if start_errors else None
        mean_end = round(sum(end_errors) / len(end_errors), 4) if end_errors else None

        return AlignmentEvaluationReport(
            language=language,
            total_annotations=total,
            matched_count=matched_count,
            within_tolerance_count=within_count,
            accuracy_pct=accuracy_pct,
            mean_start_error_sec=mean_start,
            mean_end_error_sec=mean_end,
            tolerance_sec=self.tolerance_sec,
            phrase_results=phrase_results,
        )


class WERCEREvaluator:
    """
    Computes Word Error Rate (WER) and Character Error Rate (CER) via dynamic
    programming Levenshtein distance.
    """

    @staticmethod
    def _levenshtein(seq1: list[Any], seq2: list[Any]) -> int:
        """Calculates edit distance between two sequences."""
        m, n = len(seq1), len(seq2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if seq1[i - 1] == seq2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
                else:
                    dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])

        return dp[m][n]

    @classmethod
    def calculate_wer(cls, reference: str, hypothesis: str) -> float | None:
        """
        Calculates Word Error Rate: (Substitutions + Deletions + Insertions) / Reference Words.
        Returns None if reference text is empty.
        """
        ref_words = re.sub(r"[^\w\s]", "", reference).lower().split()
        hyp_words = re.sub(r"[^\w\s]", "", hypothesis).lower().split()

        if not ref_words:
            return None

        distance = cls._levenshtein(ref_words, hyp_words)
        return round(distance / len(ref_words), 4)

    @classmethod
    def calculate_cer(cls, reference: str, hypothesis: str) -> float | None:
        """
        Calculates Character Error Rate: Edit Distance / Reference Characters.
        Returns None if reference text is empty.
        """
        ref_chars = list(re.sub(r"[\s\W]", "", reference).lower())
        hyp_chars = list(re.sub(r"[\s\W]", "", hypothesis).lower())

        if not ref_chars:
            return None

        distance = cls._levenshtein(ref_chars, hyp_chars)
        return round(distance / len(ref_chars), 4)

    @classmethod
    def evaluate(
        cls,
        reference_text: str | None,
        hypothesis_text: str,
    ) -> dict[str, Any]:
        """
        Evaluates reference against hypothesis.
        If reference_text is None or empty, returns PENDING status in accordance
        with the Zero-Hallucination policy.
        """
        if not reference_text or not reference_text.strip():
            return {
                "status": "PENDING / STAKEHOLDER INPUT REQUIRED",
                "reference_provided": False,
                "wer": None,
                "cer": None,
                "note": "Reference transcript not available in repository fixtures.",
            }

        wer = cls.calculate_wer(reference_text, hypothesis_text)
        cer = cls.calculate_cer(reference_text, hypothesis_text)

        return {
            "status": "EVALUATED",
            "reference_provided": True,
            "wer": wer,
            "cer": cer,
            "note": "",
        }
