
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.models.schemas import ChunkMetadata, DocumentChunk
from app.services.chat_history_service import ChatHistoryService


def _chunk(content: str = "History context content.") -> DocumentChunk:
    return DocumentChunk(
        content=content,
        metadata=ChunkMetadata(
            source_file="doc.pdf",
            page_number=1,
            chunk_id="doc.pdf-p1-c1",
            document_type="pdf",
        ),
    )


def test_serialize_and_deserialize_chat_history() -> None:
    """Serialization should convert DocumentChunk objects into dicts; deserialization should restore them."""
    original_history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi", "sources": [_chunk("Source info text")]},
    ]

    serialized = ChatHistoryService.serialize_chat_history(original_history)  # type: ignore[arg-type]

    # Verify serialization converted DocumentChunk to dict
    assert serialized[0]["content"] == "Hello"
    assert isinstance(serialized[1]["sources"][0], dict)
    assert serialized[1]["sources"][0]["content"] == "Source info text"
    assert serialized[1]["sources"][0]["metadata"]["source_file"] == "doc.pdf"

    # Deserialization check
    deserialized = ChatHistoryService.deserialize_chat_history(serialized)
    assert deserialized[0]["content"] == "Hello"
    assert isinstance(deserialized[1]["sources"][0], DocumentChunk)
    assert deserialized[1]["sources"][0].content == "Source info text"
    assert deserialized[1]["sources"][0].metadata.source_file == "doc.pdf"
    assert deserialized[1]["sources"][0].metadata.page_number == 1


def test_load_user_chats_returns_empty_on_missing_file(tmp_path) -> None:
    """ChatHistoryService.load_user_chats should return empty list if history file does not exist."""
    mock_settings = SimpleNamespace(chat_history_dir=tmp_path / "missing")
    with patch("app.services.chat_history_service.settings", mock_settings):
        chats = ChatHistoryService.load_user_chats("fake_user")
        assert chats == []


def test_load_user_chats_returns_list_on_valid_json(tmp_path) -> None:
    """ChatHistoryService.load_user_chats should parse history list from disk successfully."""
    dummy_data = [{"session_id": "sess-1", "title": "First Chat", "chat_history": []}]
    history_dir = tmp_path / "load"
    history_dir.mkdir(parents=True, exist_ok=True)
    history_file = history_dir / "admin_history.json"
    history_file.write_text(json.dumps(dummy_data), encoding="utf-8")

    mock_settings = SimpleNamespace(chat_history_dir=history_dir)
    with patch("app.services.chat_history_service.settings", mock_settings):
        chats = ChatHistoryService.load_user_chats("admin")
        assert chats == dummy_data
        assert len(chats) == 1
        assert chats[0]["title"] == "First Chat"


def test_save_user_chats_serializes_successfully(tmp_path) -> None:
    """ChatHistoryService.save_user_chats should dump JSON data to history file."""
    dummy_data = [
        {
            "session_id": "sess-1",
            "title": "First Chat",
            "chat_history": [],
            "created_at": "2026-07-16T12:00:00",
            "updated_at": "2026-07-16T12:00:00",
        }
    ]
    history_dir = tmp_path / "save"
    history_dir.mkdir(parents=True, exist_ok=True)
    mock_settings = SimpleNamespace(chat_history_dir=history_dir)

    with patch("app.services.chat_history_service.settings", mock_settings):
        ChatHistoryService.save_user_chats("admin", dummy_data)

    history_file = history_dir / "admin_history.json"
    assert history_file.exists()
    written_data = json.loads(history_file.read_text(encoding="utf-8"))
    assert written_data == dummy_data


def test_load_user_chats_raises_on_corrupted_json(tmp_path) -> None:
    """If the chat history JSON file is corrupted, load_user_chats must raise ChatHistoryLoadError."""
    from types import SimpleNamespace

    from app.services.chat_history_service import (
        ChatHistoryLoadError,
        ChatHistoryService,
    )

    history_dir = tmp_path / "chats"
    history_dir.mkdir()

    mock_settings = SimpleNamespace(chat_history_dir=history_dir)
    with patch("app.services.chat_history_service.settings", mock_settings):
        history_file = ChatHistoryService.get_history_file("corrupted_user")
        history_file.write_text("invalid json content {")

        with pytest.raises(
            ChatHistoryLoadError, match="Failed to decode chat history JSON"
        ):
            ChatHistoryService.load_user_chats("corrupted_user")


def test_load_user_chats_raises_on_invalid_list(tmp_path) -> None:
    """If the chat history JSON is not a list, load_user_chats must raise ChatHistoryLoadError."""
    from types import SimpleNamespace

    from app.services.chat_history_service import (
        ChatHistoryLoadError,
        ChatHistoryService,
    )

    history_dir = tmp_path / "chats"
    history_dir.mkdir()

    mock_settings = SimpleNamespace(chat_history_dir=history_dir)
    with patch("app.services.chat_history_service.settings", mock_settings):
        history_file = ChatHistoryService.get_history_file("invalid_format_user")
        history_file.write_text(json.dumps({"some_key": "some_value"}))

        with pytest.raises(ChatHistoryLoadError, match="must be a list"):
            ChatHistoryService.load_user_chats("invalid_format_user")


def test_save_user_chats_atomic(tmp_path) -> None:
    """save_user_chats must perform an atomic replace operation to prevent partial writes."""
    from app.services.chat_history_service import ChatHistoryService

    history_dir = tmp_path / "chats"
    history_dir.mkdir()

    dummy_data = [
        {
            "session_id": "sess-1",
            "title": "First Chat",
            "chat_history": [],
            "created_at": "2026-07-16T12:00:00",
            "updated_at": "2026-07-16T12:00:00",
        }
    ]

    mock_settings = SimpleNamespace(chat_history_dir=history_dir)
    with patch("app.services.chat_history_service.settings", mock_settings):
        ChatHistoryService.save_user_chats("atomic_user", dummy_data)

        history_file = ChatHistoryService.get_history_file("atomic_user")
        assert history_file.exists()

        with open(history_file, "r", encoding="utf-8") as f:
            saved = json.load(f)
        assert saved == dummy_data

        temp_file = history_file.with_suffix(".tmp")
        assert not temp_file.exists()


def test_save_user_chats_raises_on_persistence_failure(tmp_path) -> None:
    """save_user_chats should surface write failures instead of swallowing them."""
    from app.services.chat_history_service import (
        ChatHistorySaveError,
        ChatHistoryService,
    )

    history_dir = tmp_path / "chats"
    history_dir.mkdir()
    dummy_data = [{"session_id": "sess-1", "title": "First Chat", "chat_history": []}]

    mock_settings = SimpleNamespace(chat_history_dir=history_dir)
    with (
        patch("app.services.chat_history_service.settings", mock_settings),
        patch(
            "app.services.chat_history_service.os.replace",
            side_effect=OSError("disk full"),
        ),
        pytest.raises(ChatHistorySaveError, match="Failed to save chat history"),
    ):
        ChatHistoryService.save_user_chats("failing_user", dummy_data)
