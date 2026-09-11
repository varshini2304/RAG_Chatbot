"""Unit tests for chat history persistence and session management service."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.services.chat_history_service import ChatHistoryService


def test_save_and_load_chat_history(tmp_path: Path) -> None:
    """ChatHistoryService should save chat sessions to JSON file and reload them cleanly."""
    chats_dir = tmp_path / "chats"
    mock_settings = SimpleNamespace(chat_history_dir=chats_dir)

    sample_history = [
        {"role": "user", "content": "What is the policy?", "timestamp": "10:00 AM"},
        {
            "role": "assistant",
            "content": "The policy requires 2 weeks notice.",
            "timestamp": "10:01 AM",
        },
    ]

    with patch("app.services.chat_history_service.settings", mock_settings):
        # 1. Save session
        saved_sessions = ChatHistoryService.save_current_chat_to_history(
            username="testuser",
            active_session_id="session_101",
            chat_history=sample_history,
        )
        assert len(saved_sessions) == 1
        assert saved_sessions[0]["session_id"] == "session_101"

        # 2. Load user history
        loaded_sessions = ChatHistoryService.load_user_chats("testuser")
        assert len(loaded_sessions) == 1
        assert loaded_sessions[0]["chat_history"][0]["content"] == "What is the policy?"


def test_user_history_isolation(tmp_path: Path) -> None:
    """Users should only be able to view their own saved chat history files."""
    chats_dir = tmp_path / "chats"
    mock_settings = SimpleNamespace(chat_history_dir=chats_dir)

    with patch("app.services.chat_history_service.settings", mock_settings):
        ChatHistoryService.save_current_chat_to_history(
            username="alice",
            active_session_id="alice_sess_1",
            chat_history=[{"role": "user", "content": "Alice question"}],
        )
        ChatHistoryService.save_current_chat_to_history(
            username="bob",
            active_session_id="bob_sess_1",
            chat_history=[{"role": "user", "content": "Bob question"}],
        )

        alice_history = ChatHistoryService.load_user_chats("alice")
        bob_history = ChatHistoryService.load_user_chats("bob")

        assert len(alice_history) == 1
        assert len(bob_history) == 1
        assert alice_history[0]["session_id"] == "alice_sess_1"
        assert bob_history[0]["session_id"] == "bob_sess_1"


def test_delete_user_session(tmp_path: Path) -> None:
    """Deleting a session should remove it from the stored history list."""
    chats_dir = tmp_path / "chats"
    mock_settings = SimpleNamespace(chat_history_dir=chats_dir)

    with patch("app.services.chat_history_service.settings", mock_settings):
        ChatHistoryService.save_current_chat_to_history(
            username="alice",
            active_session_id="sess_1",
            chat_history=[{"role": "user", "content": "Question 1"}],
        )
        ChatHistoryService.save_current_chat_to_history(
            username="alice",
            active_session_id="sess_2",
            chat_history=[{"role": "user", "content": "Question 2"}],
        )

        updated_history = ChatHistoryService.delete_chat_session("alice", "sess_1")
        assert len(updated_history) == 1
        assert updated_history[0]["session_id"] == "sess_2"


def test_load_history_for_nonexistent_user(tmp_path: Path) -> None:
    """Loading history for a user with no saved files should return an empty list."""
    chats_dir = tmp_path / "chats"
    mock_settings = SimpleNamespace(chat_history_dir=chats_dir)

    with patch("app.services.chat_history_service.settings", mock_settings):
        assert ChatHistoryService.load_user_chats("unknown_user") == []
