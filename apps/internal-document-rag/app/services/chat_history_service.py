"""Service layer managing persistent past chat session logs for authenticated users."""

from __future__ import annotations

import json
import logging
import os
import re
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import settings
from app.models.schemas import ChunkMetadata, DocumentChunk

LOGGER = logging.getLogger(__name__)


class ChatHistoryLoadError(RuntimeError):
    """Raised when chat history file is corrupted or fails to load."""


class ChatHistorySaveError(RuntimeError):
    """Raised when chat history cannot be persisted."""


class ChatHistoryService:
    """Read, write, and serialize chat logs stored as user-scoped JSON files."""

    @classmethod
    def get_history_file(cls, username: str) -> Path:
        """Return the user-scoped chat history file path."""
        settings.chat_history_dir.mkdir(parents=True, exist_ok=True)
        sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", username.strip())
        return settings.chat_history_dir / f"{sanitized}_history.json"

    @classmethod
    def load_user_chats(cls, username: str) -> list[dict]:

        history_file = cls.get_history_file(username)
        if not history_file.exists():
            return []
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, list):
                    raise ChatHistoryLoadError("Chat history JSON must be a list.")
                for chat in data:
                    chat["chat_history"] = cls.deserialize_chat_history(
                        chat.get("chat_history", [])
                    )
                return data
        except json.JSONDecodeError as e:
            LOGGER.error("Failed to decode chat history JSON for %s: %s", username, e)
            raise ChatHistoryLoadError(
                f"Failed to decode chat history JSON: {e}"
            ) from e
        except Exception as e:
            if isinstance(e, ChatHistoryLoadError):
                raise
            LOGGER.error("Failed to load chat history for %s: %s", username, e)
            raise ChatHistoryLoadError(f"Failed to load chat history: {e}") from e

    @classmethod
    def _json_default(cls, obj: Any) -> Any:
        if hasattr(obj, "content") and hasattr(obj, "metadata"):
            meta = getattr(obj, "metadata", None)
            return {
                "content": getattr(obj, "content", ""),
                "metadata": {
                    "source_file": (
                        getattr(meta, "source_file", "unknown") if meta else "unknown"
                    ),
                    "page_number": getattr(meta, "page_number", 1) if meta else 1,
                    "chunk_id": (
                        getattr(meta, "chunk_id", "unknown") if meta else "unknown"
                    ),
                    "document_type": (
                        getattr(meta, "document_type", "pdf") if meta else "pdf"
                    ),
                },
            }
        if hasattr(obj, "source_file"):
            return {
                "source_file": getattr(obj, "source_file", "unknown"),
                "page_number": getattr(obj, "page_number", 1),
                "chunk_id": getattr(obj, "chunk_id", "unknown"),
                "document_type": getattr(obj, "document_type", "pdf"),
            }
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return str(obj)

    @classmethod
    def save_user_chats(cls, username: str, chats: list[dict]) -> None:
        """Serialize and save the list of chats to the user's history file using atomic writes."""
        history_file = cls.get_history_file(username)
        temp_file = history_file.with_suffix(".tmp")
        try:
            serialized_chats = []
            for chat in chats:
                serialized_chats.append(
                    {
                        "session_id": chat["session_id"],
                        "title": chat["title"],
                        "created_at": chat.get("created_at")
                        or datetime.now().isoformat(),
                        "updated_at": chat.get("updated_at")
                        or datetime.now().isoformat(),
                        "chat_history": cls.serialize_chat_history(
                            chat["chat_history"]
                        ),
                    }
                )

            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(
                    serialized_chats,
                    f,
                    indent=2,
                    ensure_ascii=False,
                    default=cls._json_default,
                )
                f.flush()
                os.fsync(f.fileno())  # Force commit to storage media

            os.replace(temp_file, history_file)
        except Exception as e:
            LOGGER.error("Failed to save chat history for %s: %s", username, e)
            with suppress(Exception):
                if temp_file.exists():
                    temp_file.unlink()
            raise ChatHistorySaveError(f"Failed to save chat history: {e}") from e

    @classmethod
    def serialize_chat_history(cls, history: list[dict]) -> list[dict]:
        """Convert DocumentChunk objects inside chat history messages into raw dictionaries."""
        serialized = []
        for msg in history:
            serialized_msg = msg.copy()
            sources = msg.get("sources")
            if sources:
                serialized_sources = []
                for chunk in sources:
                    if isinstance(chunk, DocumentChunk):
                        serialized_sources.append(
                            {
                                "content": chunk.content,
                                "metadata": {
                                    "source_file": chunk.metadata.source_file,
                                    "page_number": chunk.metadata.page_number,
                                    "chunk_id": chunk.metadata.chunk_id,
                                    "document_type": chunk.metadata.document_type,
                                },
                            }
                        )
                    else:
                        serialized_sources.append(chunk)
                serialized_msg["sources"] = serialized_sources
            serialized.append(serialized_msg)
        return serialized

    @classmethod
    def deserialize_chat_history(cls, history: list[dict]) -> list[dict]:
        """Convert serialized metadata dictionaries in history messages back to DocumentChunk objects."""
        deserialized = []
        for msg in history:
            deserialized_msg = msg.copy()
            sources = msg.get("sources")
            if sources:
                deserialized_sources = []
                for chunk in sources:
                    if (
                        isinstance(chunk, dict)
                        and "content" in chunk
                        and "metadata" in chunk
                    ):
                        meta = chunk["metadata"]
                        deserialized_sources.append(
                            DocumentChunk(
                                content=chunk["content"],
                                metadata=ChunkMetadata(
                                    source_file=meta.get("source_file", "unknown"),
                                    page_number=meta.get("page_number", 1),
                                    chunk_id=meta.get("chunk_id", "unknown"),
                                    document_type=meta.get("document_type", "pdf"),
                                ),
                            )
                        )
                    else:
                        deserialized_sources.append(chunk)
                deserialized_msg["sources"] = deserialized_sources
            deserialized.append(deserialized_msg)
        return deserialized

    @classmethod
    def save_current_chat_to_history(
        cls, username: str, active_session_id: str, chat_history: list[dict]
    ) -> list[dict]:
        """Save or update the active chat session record and return the updated chats catalog."""
        if not active_session_id or not chat_history:
            return cls.load_user_chats(username)

        chats = cls.load_user_chats(username)
        title = "New Chat"
        for msg in chat_history:
            if msg.get("role") == "user":
                first_q = msg.get("content", "")
                title = first_q[:30] + "..." if len(first_q) > 30 else first_q
                break

        updated = False
        for chat in chats:
            if chat.get("session_id") == active_session_id:
                chat["chat_history"] = chat_history
                if chat.get("title", "New Chat") == "New Chat":
                    chat["title"] = title
                chat["updated_at"] = datetime.now().isoformat()
                updated = True
                break

        if not updated:
            chats.append(
                {
                    "session_id": active_session_id,
                    "title": title,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "chat_history": chat_history,
                }
            )

        cls.save_user_chats(username, chats)
        return chats

    @classmethod
    def delete_chat_session(cls, username: str, session_id: str) -> list[dict]:
        """Delete the specified chat record and return the updated catalog."""
        chats = cls.load_user_chats(username)
        chats = [c for c in chats if c.get("session_id") != session_id]
        cls.save_user_chats(username, chats)
        return chats
