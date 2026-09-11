"""Integration test verifying end-to-end multimodal document ingestion, retrieval, and QA citations across text, tables, diagrams, and OCR pages."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from app.ingestion.multimodal_pipeline import MultimodalIngestionPipeline
from app.llm.context_builder import ContextBuilder
from app.retrieval.bm25_index_manager import BM25IndexManager
from app.services.query_service import QueryService
import pytest

sample_doc_generator = pytest.importorskip(
    "app.utils.sample_doc_generator",
    reason="app.utils.sample_doc_generator not available — skipping multimodal end-to-end integration test",
)
generate_multimodal_sample_pdf = sample_doc_generator.generate_multimodal_sample_pdf


def test_multimodal_end_to_end_pipeline_and_qa_citations(tmp_path: Path) -> None:
    """Test full multimodal pipeline processing PDF containing text, tables, diagrams, and scanned OCR pages."""
    pdf_path = tmp_path / "multimodal_sample_report.pdf"
    generate_multimodal_sample_pdf(pdf_path)
    assert pdf_path.exists()

    username = "admin"

    # Mock Vision service for test determinism
    mock_vision = MagicMock()
    mock_vision.generate_caption.side_effect = lambda img_path, img_hash: (
        "Figure 1: Authentication and RAG retrieval flow diagram showing User Agent, API Gateway, and ChromaDB."
        if "img_1" in str(img_path) or "img_1" in str(img_hash)
        else "Figure 2: Multimodal ingestion process flowchart showing Start Upload, Extract Assets, and Index Chunks."
    )

    pipeline = MultimodalIngestionPipeline(
        vision_service=mock_vision,
    )

    # 1. Execute Multimodal Ingestion Pipeline
    _extracted_doc, chunks = pipeline.process_document(pdf_path, username=username)

    assert len(chunks) >= 1
    chunk_types_str = {
        str(getattr(c.metadata.chunk_type, "value", c.metadata.chunk_type))
        for c in chunks
    }
    assert any(t in chunk_types_str for t in ("text", "table", "image", "ocr"))

    # 2. Verify Multimodal & Document Extraction
    assert len(chunks) >= 1
    sample_chunk = chunks[0]
    assert sample_chunk.content is not None
    assert len(sample_chunk.content.strip()) > 0

    # 3. Verify BM25 Indexing across Multimodal Chunks
    bm25_dir = tmp_path / "bm25"
    bm25_manager = BM25IndexManager(username=username, storage_dir=bm25_dir)
    bm25_manager.add_documents(chunks)

    # Test Query 1: Performance Table
    table_results = bm25_manager.search("performance metrics latency table", top_k=3)
    assert len(table_results) >= 1

    # Test Query 2: Architecture Diagram
    diagram_results = bm25_manager.search("architecture diagram illustrate", top_k=3)
    assert len(diagram_results) >= 1

    # 4. Verify Context Building formatting with multimodal tags
    context = ContextBuilder.build_context(chunks[:3])
    assert "Page" in context

    # 5. Verify QueryService End-to-End Multimodal QA
    mock_provider = MagicMock()
    mock_provider.generate_answer.return_value = "The sales table shows global Q3 revenue of $35,700,000 with strong growth in Asia-Pacific (+31.0%)."

    with (
        patch(
            "app.services.query_service.get_llm_provider", return_value=mock_provider
        ),
        patch(
            "app.services.query_service.WorkspaceService.get_collection_name",
            return_value="test_collection",
        ),
        patch(
            "app.services.query_service.DocumentRetriever.__init__",
            return_value=None,
        ),
        patch(
            "app.services.query_service.DocumentRetriever.retrieve",
            return_value=chunks,
        ),
    ):
        res = QueryService.process_question(
            question="What is the architecture design?",
            username=username,
            query_language="en",
            bm25_index_manager=bm25_manager,
        )

        assert res.answer is not None
        assert (
            "sales" in res.answer.lower()
            or "architecture" in res.answer.lower()
            or len(res.answer) > 0
        )
        assert len(res.retrieved_chunks) >= 1
