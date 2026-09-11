"""Strongly typed query response models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.models.schemas import DocumentChunk


class QueryResultKind(Enum):
    """Enumeration of grounding output classifications."""

    SUCCESS = "success"
    ERROR = "error"
    INSUFFICIENT_INFORMATION = "insufficient_information"


@dataclass
class QueryResult:
    """Grounding output details containing answer text and retrieved reference chunks."""

    answer: str
    retrieved_chunks: list[DocumentChunk]
    kind: QueryResultKind
