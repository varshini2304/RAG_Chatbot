"""Integration test for multi-turn Q&A chat flow and chat history storage persistence."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models.query_result import QueryResultKind
from app.models.schemas import ChunkMetadata, DocumentChunk
from app.services.chat_history_service import ChatHistoryService
from app.services.query_service import QueryService


def test_interactive_chat_flow_and_history_persistence(tmp_path: Path) -> None:
    """Test integrated chat lifecycle: Ask question -> Answer generated -> Save to Chat History -> Reload history."""
    chats_dir = tmp_path / "chats"
    mock_settings = SimpleNamespace(chat_history_dir=chats_dir)

    username = "alice"
    session_id = "sess_alice_2026"

    # Setup retrieval and LLM mocks
    doc_chunk = DocumentChunk(
        content="Remote work policy allows 2 days of work from home per week.",
        metadata=ChunkMetadata(
            source_file="remote_work.pdf",
            page_number=1,
            chunk_id="remote_c0",
            document_type="pdf",
        ),
    )

    mock_retriever = MagicMock()
    mock_retriever.search.return_value = [(doc_chunk, 0.9)]

    mock_llm = MagicMock()
    mock_llm.generate_answer.return_value = (
        "Remote work policy permits 2 days WFH per week."
    )

    with (
        patch("app.services.query_service.get_llm_provider", return_value=mock_llm),
        patch("app.services.chat_history_service.settings", mock_settings),
        patch(
            "app.services.query_service.DocumentRetriever.__init__", return_value=None
        ),
        patch(
            "app.services.query_service.DocumentRetriever.retrieve",
            return_value=[doc_chunk],
        ),
    ):

        # 1. Ask question via QueryService
        result = QueryService.process_question(
            "What is the WFH policy?", username=username, query_language="en"
        )
        assert result.kind in (
            QueryResultKind.SUCCESS,
            QueryResultKind.INSUFFICIENT_INFORMATION,
        )

        # 2. Append turn to session chat history
        chat_history = [
            {
                "role": "user",
                "content": "What is the WFH policy?",
                "timestamp": "10:00 AM",
            },
            {
                "role": "assistant",
                "content": "Remote work policy permits 2 days WFH per week.",
                "timestamp": "10:01 AM",
            },
        ]

        # 3. Save chat history session
        saved = ChatHistoryService.save_current_chat_to_history(
            username, session_id, chat_history
        )
        assert len(saved) == 1
        assert saved[0]["session_id"] == session_id

        # 4. Reload user sessions and verify content
        loaded = ChatHistoryService.load_user_chats(username)
        assert len(loaded) == 1
        assert (
            loaded[0]["chat_history"][1]["content"]
            == "Remote work policy permits 2 days WFH per week."
        )
