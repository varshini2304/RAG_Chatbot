"""System Test Scenario 3: Multi-Tenant Data & User Isolation."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.services.chat_history_service import ChatHistoryService


def test_system_scenario_3_multi_user_data_isolation(tmp_path: Path) -> None:
    """System Scenario 3: Verify User A cannot access User B's documents or chat history."""
    chats_dir = tmp_path / "chats"
    chats_dir.mkdir()
    mock_settings = SimpleNamespace(chat_history_dir=chats_dir)

    # 1. User A (Alice - HR) creates a session and chat history
    alice_history = [
        {
            "role": "user",
            "content": "What is the HR salary scale?",
            "timestamp": "09:00 AM",
        },
        {
            "role": "assistant",
            "content": "HR Salary scale ranges from Grade 1 to 5.",
            "timestamp": "09:01 AM",
        },
    ]

    # 2. User B (Bob - Finance) creates a session and chat history
    bob_history = [
        {
            "role": "user",
            "content": "What is the Q3 Revenue budget?",
            "timestamp": "09:05 AM",
        },
        {
            "role": "assistant",
            "content": "Q3 Revenue budget is $2.5 Million.",
            "timestamp": "09:06 AM",
        },
    ]

    with patch("app.services.chat_history_service.settings", mock_settings):
        ChatHistoryService.save_current_chat_to_history(
            "alice", "alice_session_1", alice_history
        )
        ChatHistoryService.save_current_chat_to_history(
            "bob", "bob_session_1", bob_history
        )

        # Verify User A loads ONLY User A's history
        alice_loaded = ChatHistoryService.load_user_chats("alice")
        assert len(alice_loaded) == 1
        assert alice_loaded[0]["session_id"] == "alice_session_1"
        assert "salary scale" in alice_loaded[0]["chat_history"][0]["content"].lower()

        # Verify User B loads ONLY User B's history
        bob_loaded = ChatHistoryService.load_user_chats("bob")
        assert len(bob_loaded) == 1
        assert bob_loaded[0]["session_id"] == "bob_session_1"
        assert "revenue budget" in bob_loaded[0]["chat_history"][0]["content"].lower()

        # Ensure Bob cannot see Alice's session and vice-versa
        assert not any(s["session_id"] == "alice_session_1" for s in bob_loaded)
        assert not any(s["session_id"] == "bob_session_1" for s in alice_loaded)
