"""In-memory and persisted BM25 keyword index manager for RAG workspaces."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi  # type: ignore[import-not-found, import-untyped]

from app.config import settings
from app.models.schemas import ChunkMetadata, ChunkType, DocumentChunk

LOGGER = logging.getLogger(__name__)


class BM25IndexManager:

    def __init__(self, username: str, storage_dir: Path | None = None) -> None:
        self.username = username
        self.storage_dir = storage_dir or (settings.data_dir / "bm25_index" / username)
        self.corpus_file = self.storage_dir / "corpus.json"

        # In-memory index states
        self._tokenized_corpus: list[list[str]] = []
        self._chunk_ids: list[str] = []
        self._chunk_map: dict[str, DocumentChunk] = {}
        self._bm25: BM25Okapi | None = None

    def load(self) -> None:
        """Load persisted index from storage, if it exists."""
        self._tokenized_corpus = []
        self._chunk_ids = []
        self._chunk_map = {}
        self._bm25 = None

        if self.corpus_file.exists():
            try:
                with open(self.corpus_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._tokenized_corpus = data.get("tokenized_corpus", [])
                    self._chunk_ids = data.get("chunk_ids", [])
                    serialized_chunks = data.get("chunks_by_id", {})
                    self._chunk_map = self._deserialize_chunk_map(serialized_chunks)

                    if self._tokenized_corpus:
                        self._bm25 = BM25Okapi(self._tokenized_corpus)
                LOGGER.info(
                    "Successfully loaded BM25 index from disk for user: %s",
                    self.username,
                )
            except Exception as exc:  # noqa: BLE001
                LOGGER.error("Failed to load BM25 index for %s: %s", self.username, exc)

    def _save(self) -> None:
        """Persist the tokenized corpus to disk as JSON."""
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            data = {
                "tokenized_corpus": self._tokenized_corpus,
                "chunk_ids": self._chunk_ids,
                "chunks_by_id": self._serialize_chunk_map(),
            }
            with open(self.corpus_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            LOGGER.info(
                "Successfully persisted BM25 index to disk for user: %s", self.username
            )
        except Exception as exc:  # noqa: BLE001
            LOGGER.error("Failed to save BM25 index for %s: %s", self.username, exc)

    @staticmethod
    def _normalize_chunk_type(value: Any) -> ChunkType:
        """Convert persisted chunk type values into a valid enum member."""
        try:
            return ChunkType(value)
        except Exception:  # noqa: BLE001
            return ChunkType.TEXT

    def _serialize_chunk_map(self) -> dict[str, dict[str, Any]]:
        """Serialize persisted chunks keyed by chunk ID for reload-safe BM25 search."""
        serialized: dict[str, dict[str, Any]] = {}
        for chunk_id in self._chunk_ids:
            chunk = self._chunk_map.get(chunk_id)
            if chunk is None:
                continue
            serialized[chunk_id] = {
                "content": chunk.content,
                "metadata": chunk.metadata.model_dump(mode="json", exclude_none=True),
            }
        return serialized

    def _deserialize_chunk_map(
        self, raw_chunks: dict[str, dict[str, Any]]
    ) -> dict[str, DocumentChunk]:
        """Rebuild chunk objects from persisted JSON payloads."""
        chunk_map: dict[str, DocumentChunk] = {}
        for chunk_id, payload in raw_chunks.items():
            if not isinstance(payload, dict):
                continue
            metadata_payload = payload.get("metadata", {})
            if not isinstance(metadata_payload, dict):
                metadata_payload = {}
            metadata_payload = dict(metadata_payload)
            metadata_payload["chunk_type"] = self._normalize_chunk_type(
                metadata_payload.get("chunk_type", "text")
            )
            metadata_payload.setdefault("chunk_id", chunk_id)
            try:
                chunk_map[chunk_id] = DocumentChunk(
                    content=str(payload.get("content", "")),
                    metadata=ChunkMetadata(**metadata_payload),
                )
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning(
                    "Skipping persisted BM25 chunk %s for user %s: %s",
                    chunk_id,
                    self.username,
                    exc,
                )
        return chunk_map

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Tokenize text for BM25. Supports English and Japanese."""
        text_lower = text.lower()
        # Japanese character ranges (Hiragana, Katakana, Kanji)
        if re.search(r"[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9faf]", text_lower):
            # Japanese: character-based tokenization (unigrams + bigrams)
            unigrams = list(text_lower)
            bigrams = [text_lower[i : i + 2] for i in range(len(text_lower) - 1)]
            return [
                t.strip()
                for t in (unigrams + bigrams)
                if t.strip() and t.strip().isalnum()
            ]
        else:
            # English/other: whitespace & alphanumeric word tokenization
            return re.findall(r"\w+", text_lower)

    def update_chunk_map(self, chunks: Sequence[DocumentChunk]) -> None:
        """Update the in-memory mapping from chunk ID to DocumentChunk."""
        for chunk in chunks:
            self._chunk_map[chunk.metadata.chunk_id] = chunk

    def add_documents(self, chunks: list[DocumentChunk]) -> None:
        """Tokenize and append chunks to the in-memory index, then persist."""
        if not chunks:
            LOGGER.debug("add_documents called with empty chunks list")
            return

        LOGGER.debug("add_documents: adding %d chunks", len(chunks))
        for chunk in chunks:
            cid = chunk.metadata.chunk_id
            content = chunk.content

            # If chunk already exists, remove it first to prevent duplicates
            if cid in self._chunk_ids:
                idx = self._chunk_ids.index(cid)
                self._tokenized_corpus.pop(idx)
                self._chunk_ids.pop(idx)

            self._chunk_map[cid] = chunk
            tokens = self._tokenize(content)
            LOGGER.debug("add_documents: chunk %s tokenized to %s", cid, tokens)
            self._tokenized_corpus.append(tokens)
            self._chunk_ids.append(cid)

        LOGGER.debug(
            "add_documents: final state - %d chunks, %d tokens in corpus",
            len(self._chunk_ids),
            len(self._tokenized_corpus),
        )
        if self._tokenized_corpus:
            self._bm25 = BM25Okapi(self._tokenized_corpus)
            LOGGER.debug("add_documents: BM25 index created successfully")
        else:
            self._bm25 = None
            LOGGER.debug("add_documents: BM25 index is None due to empty corpus")

        self._save()

    def remove_document_by_source(self, source_file: str) -> None:

        indices_to_remove = []
        for idx, cid in enumerate(self._chunk_ids):
            chunk = self._chunk_map.get(cid)
            if chunk and chunk.metadata.source_file == source_file:
                indices_to_remove.append(idx)

        # Remove from collections in reverse order to preserve indexing
        for idx in sorted(indices_to_remove, reverse=True):
            cid = self._chunk_ids[idx]
            self._tokenized_corpus.pop(idx)
            self._chunk_ids.pop(idx)
            self._chunk_map.pop(cid, None)

        if self._tokenized_corpus:
            self._bm25 = BM25Okapi(self._tokenized_corpus)
        else:
            self._bm25 = None

        self._save()

    def clear(self) -> None:
        """Clear all in-memory state and wipe the persisted index file."""
        self._tokenized_corpus = []
        self._chunk_ids = []
        self._chunk_map = {}
        self._bm25 = None

        try:
            self.corpus_file.unlink(missing_ok=True)
            LOGGER.info("Deleted BM25 index file for user %s.", self.username)
        except Exception as exc:  # noqa: BLE001
            LOGGER.error("Failed to delete BM25 index file: %s", exc)

    def search(self, normalized_query: str, top_k: int) -> list[DocumentChunk]:
        """Query the already loaded in-memory index."""
        if not self._bm25 or not self._tokenized_corpus:
            LOGGER.debug(
                "search: returning empty - bm25=%s, corpus_size=%d",
                self._bm25 is not None,
                len(self._tokenized_corpus),
            )
            return []

        tokenized_query = self._tokenize(normalized_query)
        LOGGER.debug(
            "search: query=%s, tokenized=%s", normalized_query, tokenized_query
        )
        scores = self._bm25.get_scores(tokenized_query)
        LOGGER.debug("search: got %d scores", len(scores))

        query_set = set(tokenized_query)
        paired = []
        for idx, (cid, score) in enumerate(zip(self._chunk_ids, scores)):
            doc_tokens = self._tokenized_corpus[idx]
            has_overlap = any(token in query_set for token in doc_tokens)
            if score > 0 or has_overlap:
                chunk = self._chunk_map.get(cid)
                if chunk:
                    effective_score = max(score, 0.0)
                    LOGGER.debug(
                        "search: matched chunk %s with score %.4f (has_overlap=%s)",
                        cid,
                        effective_score,
                        has_overlap,
                    )
                    paired.append((chunk, effective_score))
                else:
                    LOGGER.debug("search: match but chunk %s not in map", cid)

        # Sort by score descending
        paired.sort(key=lambda x: x[1], reverse=True)
        result = [item[0] for item in paired[:top_k]]
        LOGGER.debug("search: returning %d results", len(result))
        return result
