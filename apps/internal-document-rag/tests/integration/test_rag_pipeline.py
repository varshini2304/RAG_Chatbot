"""Integration test for Workflow 2: User Question -> Preprocessing -> Hybrid Retrieval -> Prompt Builder -> LLM Answer."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.models.query_result import QueryResultKind
from app.models.schemas import ChunkMetadata, DocumentChunk
from app.services.query_service import QueryService


def test_complete_rag_query_pipeline_integration() -> None:
    """Test full RAG flow: Question input -> Preprocessor -> Retrieval -> Prompt -> LLM response."""
    question = "What are the working hours?"
    username = "admin"
    query_language = "en"

    # Mock chunk returned by search
    doc_chunk = DocumentChunk(
        content="Working hours are Monday through Friday from 9 AM to 5 PM EST.",
        metadata=ChunkMetadata(
            source_file="working_hours.pdf",
            page_number=1,
            chunk_id="working_hours.pdf-p1-c1",
            document_type="pdf",
        ),
    )

    # Mock LLM Provider and DocumentRetriever
    mock_llm_provider = MagicMock()
    mock_llm_provider.provider_name = "gemini"
    mock_llm_provider.generate_answer.return_value = "Based on the company document, working hours are Monday through Friday from 9 AM to 5 PM EST."

    mock_retriever = MagicMock()
    mock_retriever.retrieve.return_value = [doc_chunk]

    with (
        patch(
            "app.services.query_service.DocumentRetriever", return_value=mock_retriever
        ),
        patch(
            "app.services.query_service.get_llm_provider",
            return_value=mock_llm_provider,
        ),
    ):
        result = QueryService.process_question(
            question=question,
            username=username,
            query_language=query_language,
        )

        assert result.kind == QueryResultKind.SUCCESS
        assert "9 AM to 5 PM EST" in result.answer
        assert len(result.retrieved_chunks) == 1
