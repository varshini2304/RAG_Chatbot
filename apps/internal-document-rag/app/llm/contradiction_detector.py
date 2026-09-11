"""Contradiction detection across retrieved document chunks.

Makes a single lightweight LLM call to detect factual conflicts when the
top-K chunks originate from more than one source document.  The check is
skipped entirely when all chunks share the same source file, or when the
feature is disabled via ``settings.enable_contradiction_detection``.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.config import settings

LOGGER = logging.getLogger(__name__)

# Maximum number of chunks sent to the detector (controls token cost).
_MAX_CHUNKS = 5

_PROMPT_TEMPLATE = """\
You are a factual consistency checker. Below are text excerpts from different documents. \
Determine whether any two excerpts contain a DIRECT factual contradiction — \
a case where one excerpt asserts something that the other explicitly denies or contradicts on the same specific fact.

Excerpts:
{excerpts}

Reply with ONLY valid JSON in this exact format (no markdown, no commentary):
{{"contradiction": true/false, "summary": "one-sentence description of the conflict, or null if none"}}"""


def _build_excerpts(chunks: list[Any]) -> str:
    """Format a list of DocumentChunk objects into numbered excerpts for the prompt."""
    lines = []
    for i, item in enumerate(chunks, start=1):
        chunk = item[0] if isinstance(item, (list, tuple)) else item
        metadata = getattr(chunk, "metadata", None)
        source = getattr(metadata, "source_file", "unknown") if metadata else "unknown"
        content = str(getattr(chunk, "content", chunk))
        lines.append(f"[{i}] Source: {source}\n{content}")
    return "\n\n".join(lines)


def _parse_response(raw: str) -> dict[str, Any]:
    """Extract the JSON payload from the LLM response, tolerating minor formatting."""
    raw = raw.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        data = json.loads(raw)
        return {
            "contradiction": bool(data.get("contradiction", False)),
            "summary": data.get("summary") or None,
        }
    except (json.JSONDecodeError, AttributeError, TypeError) as exc:
        LOGGER.warning("Contradiction detector could not parse LLM response: %s | raw=%r", exc, raw)
        return {"contradiction": False, "summary": None}


def detect_contradictions(
    chunks: list[Any],
    provider: Any,
) -> dict[str, Any]:
    """Check whether the top-K chunks contain a direct factual contradiction.

    Args:
        chunks: Post-RRF retrieved chunks (``DocumentChunk`` or ``(chunk, score)``
            tuples) that will be used to build the LLM context.
        provider: Active LLM provider instance (must implement ``generate_answer``).

    Returns:
        A dict with keys:
        - ``"contradiction"`` (bool) — True when a conflict was detected.
        - ``"summary"`` (str | None) — Human-readable description of the
          conflict, or None when no contradiction was found.
        - ``"skipped"`` (bool) — True when the check was not executed
          (all same source, or fewer than 2 chunks).
    """
    if not settings.enable_contradiction_detection:
        return {"contradiction": False, "summary": None, "skipped": True}

    if not chunks or len(chunks) < 2:
        return {"contradiction": False, "summary": None, "skipped": True}

    # Collect unique source files from the top-N chunks
    top_chunks = chunks[:_MAX_CHUNKS]
    source_files: set[str] = set()
    for item in top_chunks:
        chunk = item[0] if isinstance(item, (list, tuple)) else item
        metadata = getattr(chunk, "metadata", None)
        source = getattr(metadata, "source_file", None) if metadata else None
        if source:
            source_files.add(source)

    if len(source_files) < 2:
        LOGGER.debug(
            "Contradiction check skipped: all top chunks from same source (%s)",
            source_files,
        )
        return {"contradiction": False, "summary": None, "skipped": True}

    excerpts = _build_excerpts(top_chunks)
    prompt = _PROMPT_TEMPLATE.format(excerpts=excerpts)

    try:
        # Use a neutral context; the whole question IS the prompt here.
        raw_response = provider.generate_answer(
            question=prompt,
            context="",
            query_language="en",
        )
    except Exception as exc:
        LOGGER.warning("Contradiction detector LLM call failed: %s", exc)
        return {"contradiction": False, "summary": None, "skipped": True}

    result = _parse_response(raw_response)
    result["skipped"] = False

    if result["contradiction"]:
        LOGGER.info(
            "Contradiction detected across sources %s: %s",
            sorted(source_files),
            result["summary"],
        )
    else:
        LOGGER.debug("No contradiction detected across sources %s", sorted(source_files))

    return result
