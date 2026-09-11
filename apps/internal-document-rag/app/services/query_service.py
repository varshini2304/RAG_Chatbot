from __future__ import annotations

import logging
import re
from typing import Any, ClassVar

from app.llm import ContextBuilder, get_llm_provider
from app.models.query_result import QueryResult, QueryResultKind
from app.retrieval.retriever import DocumentRetriever
from app.services.workspace_service import WorkspaceService
from app.utils.localization import get_message

LOGGER = logging.getLogger(__name__)


class QueryService:
    """Orchestrate semantic search and prompt-grounded QA generation workflows."""

    _RELEVANCE_STOPWORDS: ClassVar[set[str]] = {
        "what",
        "which",
        "who",
        "when",
        "where",
        "why",
        "how",
        "is",
        "are",
        "was",
        "were",
        "the",
        "a",
        "an",
        "of",
        "to",
        "in",
        "on",
        "for",
        "and",
        "or",
        "does",
        "do",
        "did",
    }

    @staticmethod
    def _normalize_answer(answer: str) -> str:
        """Normalize provider output for stable comparison against canonical refusal messages."""
        normalized = re.sub(r"\s+", " ", answer).strip()
        return normalized.strip("\"'").strip("\u201c\u201d")

    @classmethod
    def _is_insufficient_information_answer(cls, answer: str) -> bool:
        """Detect canonical refusal responses even if the provider adds harmless formatting."""
        normalized_answer = cls._normalize_answer(answer)
        canonical_answers = {
            cls._normalize_answer(get_message("empty_context", "en")),
            cls._normalize_answer(get_message("empty_context", "ja")),
        }
        return normalized_answer in canonical_answers

    @classmethod
    def _is_retrieval_relevant(cls, question: str, chunks: list[Any]) -> bool:
        """Verify retrieved chunks contain minimum relevance prior to LLM invocation."""
        if not chunks:
            return False
        if any(ord(char) > 127 for char in question):
            return True
        query_terms = {
            token.lower()
            for token in re.findall(r"\w+", question)
            if len(token) > 2 and token.lower() not in cls._RELEVANCE_STOPWORDS
        }
        if not query_terms:
            return bool(chunks)
        for item in chunks:
            chunk = item[0] if isinstance(item, (list, tuple)) else item
            content = str(getattr(chunk, "content", chunk)).lower()
            if any(term in content for term in query_terms):
                return True
        return False

    @classmethod
    def process_question(
        cls,
        question: str,
        username: str,
        query_language: str,
        bm25_index_manager: Any = None,
        offline_mode: bool | None = None,
    ) -> QueryResult:
        """Query user collection, build grounding context, and generate grounded answer."""
        cleaned_question = question.strip()
        word_count = len(cleaned_question.split())

        print("\n" + "=" * 60)
        print("RAG QUERY START")
        print("=" * 60)
        print(f"[1] QUESTION\n    {cleaned_question}")
        print(f"[2] QUERY VALIDATION\n    Word count: {word_count}\n    Status: PASS")

        try:
            if offline_mode is not None:
                router = get_llm_provider()
                if hasattr(router, "set_offline_mode"):
                    router.set_offline_mode(offline_mode)

            collection_name = WorkspaceService.get_collection_name(username)
            from app.retrieval.bm25_index_manager import BM25IndexManager

            if bm25_index_manager is None:
                try:
                    bm25_index_manager = BM25IndexManager(username=username)
                    bm25_index_manager.load()
                except Exception as exc:
                    LOGGER.warning(
                        "Could not auto-load BM25 index manager for %s: %s",
                        username,
                        exc,
                    )
            elif (
                isinstance(bm25_index_manager, BM25IndexManager)
                and bm25_index_manager._bm25 is None
            ):
                try:
                    bm25_index_manager.load()
                except Exception as exc:
                    LOGGER.warning(
                        "Could not load BM25 corpus for %s: %s", username, exc
                    )

            retriever = DocumentRetriever(
                collection_name=collection_name,
                bm25_index_manager=bm25_index_manager,
            )
            from app.retrieval.retrieval_engine import InsufficientInformationError

            try:
                retrieved_chunks = retriever.retrieve(cleaned_question, top_k=None)
            except InsufficientInformationError:
                retrieved_chunks = []

            # Perform pre-LLM relevance verification check
            if not retrieved_chunks or not cls._is_retrieval_relevant(
                cleaned_question, retrieved_chunks
            ):
                print("    Query validation: FAILED (Insufficient information in retrieved chunks)")
                print("=" * 60)
                print("RAG QUERY STOPPED")
                print("=" * 60 + "\n")
                error_msg = get_message("empty_context", query_language)
                return QueryResult(
                    answer=error_msg,
                    retrieved_chunks=[],
                    kind=QueryResultKind.INSUFFICIENT_INFORMATION,
                )

            # [7] FINAL RETRIEVAL LOGGING
            print(f"[7] FINAL RETRIEVAL\n    Selected chunks: {len(retrieved_chunks)}")
            for idx, chunk in enumerate(retrieved_chunks, start=1):
                src = getattr(chunk.metadata, "source_file", "unknown")
                page = getattr(chunk.metadata, "page_number", 1)
                print(f"    {idx}. {src} | Page {page}")

            provider = get_llm_provider()

            # Contradiction detection — runs only when chunks come from 2+ source files.
            from app.llm.contradiction_detector import detect_contradictions

            contradiction_result = detect_contradictions(retrieved_chunks, provider)

            # [8] CONTEXT BUILDING LOGGING
            print("Building LLM context...")
            context_str = ContextBuilder.build_context(retrieved_chunks)
            print(f"[8] CONTEXT BUILDING\n    Chunks used: {len(retrieved_chunks)}\n    Context characters: {len(context_str):,}")

            # [9 & 10] LLM GENERATION
            prov_name = getattr(provider, "provider_name", "Unknown")
            mod_name = getattr(provider, "model_name", "Unknown")
            print(f"[9] LLM GENERATION\n    Provider: {prov_name}\n    Model: {mod_name}\n    Sending context to LLM...")

            if hasattr(provider, "generate_answer"):
                answer = provider.generate_answer(
                    cleaned_question,
                    context_str,
                    query_language=query_language,
                )
            elif hasattr(provider, "generate_response"):
                answer = provider.generate_response(
                    cleaned_question,
                    None,
                )
            else:
                raise AttributeError(
                    "LLM provider must implement generate_answer or generate_response"
                )

            kind = QueryResultKind.SUCCESS
            if cls._is_insufficient_information_answer(answer):
                kind = QueryResultKind.INSUFFICIENT_INFORMATION
                answer = get_message("empty_context", query_language)

            # Annotate answer when a contradiction was detected
            if (
                contradiction_result.get("contradiction")
                and not contradiction_result.get("skipped")
                and kind == QueryResultKind.SUCCESS
            ):
                summary = contradiction_result.get("summary") or "conflicting claims found"
                answer = (
                    f"⚠️ Note: your documents contain conflicting information on this "
                    f"topic — {summary}\n\n{answer}"
                )

            print(f"[10] RESPONSE\n     Generated successfully\n     Response characters: {len(answer):,}")
            print(f"[11] SOURCES\n     References: {len(retrieved_chunks)}")
            print("=" * 60)
            print("RAG QUERY COMPLETE")
            print("=" * 60 + "\n")

            LOGGER.info(
                "QUERY PROCESSED | User: %s | Question: %r | Provider: %s | Retrieved Chunks: %d | Generated Answer: %r",
                username,
                cleaned_question,
                prov_name,
                len(retrieved_chunks),
                answer,
            )

            return QueryResult(
                answer=answer, retrieved_chunks=retrieved_chunks, kind=kind
            )

        except Exception as exc:
            print(f"[ERROR] RAG QUERY FAILED: {exc}")
            print("=" * 60)
            print("RAG QUERY FAILED")
            print("=" * 60 + "\n")
            LOGGER.exception("Error processing question in QueryService:")
            from app.llm.exceptions import ProviderRateLimitError

            if isinstance(exc, ProviderRateLimitError):
                error_msg = get_message("rate_limited", query_language)
                return QueryResult(
                    answer=error_msg, retrieved_chunks=[], kind=QueryResultKind.ERROR
                )
            return QueryResult(
                answer=str(exc), retrieved_chunks=[], kind=QueryResultKind.ERROR
            )
