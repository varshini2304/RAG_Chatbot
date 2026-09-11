"""Tests for the contradiction detector module."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.llm.contradiction_detector import detect_contradictions, _parse_response
from app.models.schemas import ChunkMetadata, DocumentChunk


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_chunk(content: str, source_file: str, page: int = 1) -> DocumentChunk:
    return DocumentChunk(
        content=content,
        metadata=ChunkMetadata(
            source_file=source_file,
            page_number=page,
            chunk_id=f"{source_file}-p{page}-c1",
            document_type="txt",
        ),
    )


def _mock_provider(response: str) -> MagicMock:
    """Return a mock LLM provider that returns *response* from generate_answer."""
    provider = MagicMock()
    provider.generate_answer.return_value = response
    return provider


# ---------------------------------------------------------------------------
# _parse_response unit tests
# ---------------------------------------------------------------------------

def test_parse_response_valid_contradiction():
    raw = json.dumps({"contradiction": True, "summary": "Doc A says 10 days; Doc B says 5 days."})
    result = _parse_response(raw)
    assert result["contradiction"] is True
    assert "10 days" in result["summary"]


def test_parse_response_no_contradiction():
    raw = json.dumps({"contradiction": False, "summary": None})
    result = _parse_response(raw)
    assert result["contradiction"] is False
    assert result["summary"] is None


def test_parse_response_markdown_fenced():
    raw = "```json\n{\"contradiction\": true, \"summary\": \"conflict\"}\n```"
    result = _parse_response(raw)
    assert result["contradiction"] is True


def test_parse_response_malformed_returns_safe_default():
    result = _parse_response("not json at all")
    assert result["contradiction"] is False
    assert result["summary"] is None


# ---------------------------------------------------------------------------
# detect_contradictions: skip conditions
# ---------------------------------------------------------------------------

def test_skips_when_all_chunks_same_source():
    """No LLM call should be made when all chunks come from one file."""
    chunk_a = _make_chunk("Employees get 10 days leave.", "policy.txt")
    chunk_b = _make_chunk("Annual leave is 10 days per year.", "policy.txt")
    provider = _mock_provider("")

    result = detect_contradictions([chunk_a, chunk_b], provider)

    assert result["skipped"] is True
    assert result["contradiction"] is False
    provider.generate_answer.assert_not_called()


def test_skips_when_fewer_than_two_chunks():
    chunk = _make_chunk("Only one chunk.", "policy.txt")
    provider = _mock_provider("")

    result = detect_contradictions([chunk], provider)

    assert result["skipped"] is True
    provider.generate_answer.assert_not_called()


def test_skips_when_empty_list():
    provider = _mock_provider("")
    result = detect_contradictions([], provider)
    assert result["skipped"] is True
    provider.generate_answer.assert_not_called()


def test_skips_when_feature_disabled():
    chunk_a = _make_chunk("10 days leave.", "hr_policy.txt")
    chunk_b = _make_chunk("5 days leave.", "employee_handbook.txt")
    provider = _mock_provider("")

    with patch("app.llm.contradiction_detector.settings") as mock_settings:
        mock_settings.enable_contradiction_detection = False
        result = detect_contradictions([chunk_a, chunk_b], provider)

    assert result["skipped"] is True
    provider.generate_answer.assert_not_called()


# ---------------------------------------------------------------------------
# detect_contradictions: contradiction fires
# ---------------------------------------------------------------------------

def test_contradiction_detected_across_two_sources():
    """Two chunks from different files with obvious factual conflict."""
    chunk_a = _make_chunk(
        "Employees are entitled to 10 days of annual leave.",
        "hr_policy.txt",
    )
    chunk_b = _make_chunk(
        "The employee handbook states annual leave is 5 days.",
        "employee_handbook.txt",
    )
    llm_response = json.dumps(
        {
            "contradiction": True,
            "summary": "hr_policy.txt says 10 days; employee_handbook.txt says 5 days.",
        }
    )
    provider = _mock_provider(llm_response)

    result = detect_contradictions([chunk_a, chunk_b], provider)

    assert result["contradiction"] is True
    assert result["skipped"] is False
    assert "10 days" in result["summary"] or "5 days" in result["summary"]
    provider.generate_answer.assert_called_once()


def test_no_contradiction_across_two_sources():
    """Two chunks from different files with consistent facts."""
    chunk_a = _make_chunk("Annual leave is 15 days.", "policy_v1.txt")
    chunk_b = _make_chunk("Staff receive 15 days of annual leave.", "policy_v2.txt")
    llm_response = json.dumps({"contradiction": False, "summary": None})
    provider = _mock_provider(llm_response)

    result = detect_contradictions([chunk_a, chunk_b], provider)

    assert result["contradiction"] is False
    assert result["skipped"] is False
    provider.generate_answer.assert_called_once()


def test_llm_failure_returns_safe_default():
    """If the LLM call throws, detect_contradictions returns no contradiction."""
    chunk_a = _make_chunk("10 days leave.", "hr.txt")
    chunk_b = _make_chunk("5 days leave.", "handbook.txt")
    provider = MagicMock()
    provider.generate_answer.side_effect = RuntimeError("network timeout")

    result = detect_contradictions([chunk_a, chunk_b], provider)

    assert result["contradiction"] is False
    assert result["skipped"] is True


def test_only_top_five_chunks_sent_to_llm():
    """The detector caps at _MAX_CHUNKS=5 regardless of how many are passed."""
    chunks = [
        _make_chunk(f"Content {i}", f"file_{i}.txt") for i in range(10)
    ]
    provider = _mock_provider(json.dumps({"contradiction": False, "summary": None}))

    detect_contradictions(chunks, provider)

    # Only one LLM call should happen
    provider.generate_answer.assert_called_once()
    call_kwargs = provider.generate_answer.call_args
    prompt = call_kwargs[1].get("question") or call_kwargs[0][0]
    # At most 5 sources should appear (file_0 through file_4)
    assert "file_5.txt" not in prompt
    assert "file_6.txt" not in prompt
