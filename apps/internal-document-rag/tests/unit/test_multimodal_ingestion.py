"""Unit tests for Multimodal Ingestion Pipeline, Vision, Table, and OCR modules."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.ingestion.multimodal_pipeline import MultimodalIngestionPipeline
from app.llm.context_builder import ContextBuilder
from app.models.schemas import (
    ChunkMetadata,
    ChunkType,
    DocumentAsset,
    DocumentChunk,
    ExtractedPage,
    ExtractedPdfDocument,
)
from app.ingestion.table_extractor import TableExtractor
from app.vision.caption_cache import ImageCaptionCache
from app.vision.vision_engine import VisionEngine, VisionService


def test_chunk_type_enum_values() -> None:
    """ChunkType enum should define all required multimodal types."""
    assert ChunkType.TEXT.value == "text"
    assert ChunkType.IMAGE.value == "image"
    assert ChunkType.TABLE.value == "table"
    assert ChunkType.OCR.value == "ocr"
    assert ChunkType.DIAGRAM.value == "diagram"
    assert ChunkType.CHART.value == "chart"


def test_generate_sample_multimodal_documents(tmp_path: Path) -> None:
    """Ensure unique, user-customized multimodal PDF sample documents are generated for each user workspace."""
    import shutil

    sample_doc_generator = pytest.importorskip(
        "app.utils.sample_doc_generator",
        reason="app.utils.sample_doc_generator not available",
    )
    generate_multimodal_sample_pdf = sample_doc_generator.generate_multimodal_sample_pdf

    base_dir = tmp_path / "sample_docs"
    shutil.rmtree(base_dir, ignore_errors=True)
    base_dir.mkdir(parents=True, exist_ok=True)
    user_configs = [
        (base_dir / "multimodal_system_architecture_and_sales_report.pdf", "admin"),
        (
            base_dir / "admin" / "multimodal_system_architecture_and_sales_report.pdf",
            "admin",
        ),
        (
            base_dir / "varsh" / "multimodal_system_architecture_and_sales_report.pdf",
            "varsh",
        ),
        (
            base_dir
            / "varshini"
            / "multimodal_system_architecture_and_sales_report.pdf",
            "varshini",
        ),
    ]

    for path, preset in user_configs:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.unlink(missing_ok=True)
        generate_multimodal_sample_pdf(path, user_preset=preset)
        assert path.exists()


def test_document_asset_model_instantiation() -> None:
    """DocumentAsset model should validate asset metadata fields."""
    asset = DocumentAsset(
        asset_type=ChunkType.IMAGE,
        page_number=2,
        content="[Architecture Diagram]",
        source_file="design.pdf",
        document_name="design.pdf",
        username="admin",
        image_path="/tmp/page_2.png",
        image_hash="a1b2c3d4",
        image_dimensions=(800, 600),
    )
    assert asset.asset_type == ChunkType.IMAGE
    assert asset.page_number == 2
    assert asset.image_hash == "a1b2c3d4"


def test_image_caption_cache_operations(tmp_path: Path) -> None:
    """ImageCaptionCache should load, store, and persist SHA-256 captions."""
    cache_file = tmp_path / "test_captions.json"
    cache = ImageCaptionCache(cache_file=cache_file)

    assert cache.get("hash_123") is None
    cache.set("hash_123", "Flowchart showing auth pipeline")
    assert cache.get("hash_123") == "Flowchart showing auth pipeline"

    # Reload from disk
    cache2 = ImageCaptionCache(cache_file=cache_file)
    assert cache2.get("hash_123") == "Flowchart showing auth pipeline"


def test_vision_service_uses_cache(tmp_path: Path) -> None:
    """VisionService should return cached captions without calling LLM APIs."""
    cache = ImageCaptionCache(cache_file=tmp_path / "cache.json")
    cache.set("img_hash_999", "Pre-computed vision caption")

    service = VisionService(cache=cache)
    img_file = tmp_path / "sample.png"
    img_file.write_bytes(b"dummy image bytes")

    caption = service.generate_caption(img_file, image_hash="img_hash_999")
    assert caption == "Pre-computed vision caption"


def test_vision_service_refreshes_fallback_cache(tmp_path: Path) -> None:
    """Fallback captions should be replaced when a better provider result is available."""
    cache = ImageCaptionCache(cache_file=tmp_path / "cache.json")
    cache.set(
        "img_hash_111",
        "Visual Diagram/Graphic Asset (Image File: sample.png). Contains architectural workflow components.",
    )
    service = VisionService(cache=cache)
    img_file = tmp_path / "sample.png"
    img_file.write_bytes(b"dummy image bytes")

    with patch.object(
        service,
        "_generate_with_gemini",
        return_value="User -> Auth Service -> Retriever -> LLM",
    ):
        caption = service.generate_caption(img_file, image_hash="img_hash_111")

    assert caption == "User -> Auth Service -> Retriever -> LLM"
    assert cache.get("img_hash_111") == caption


def test_table_extractor_markdown_json_formatting() -> None:
    """TableExtractor should format raw rows into valid Markdown and JSON strings."""
    raw_rows: list[list[str | None]] = [
        ["Quarter", "Revenue", "Profit"],
        ["Q1", "$10M", "$2M"],
        ["Q2", "$12M", "$3M"],
    ]
    md_str, json_str = TableExtractor._format_table_outputs(raw_rows)

    assert "| Quarter | Revenue | Profit |" in md_str
    assert "| Q1 | $10M | $2M |" in md_str
    assert '"Quarter": "Q1"' in json_str or '"Q1"' in json_str


def test_context_builder_multimodal_demarcations() -> None:
    """ContextBuilder should include [TEXT], [IMAGE], [TABLE], [OCR] type tags."""
    text_chunk = DocumentChunk(
        content="Standard policy details.",
        metadata=ChunkMetadata(
            source_file="doc.pdf",
            page_number=1,
            chunk_id="c1",
            document_type="pdf",
            chunk_type=ChunkType.TEXT,
        ),
    )
    img_chunk = DocumentChunk(
        content="Diagram of backend microservices.",
        metadata=ChunkMetadata(
            source_file="doc.pdf",
            page_number=3,
            chunk_id="c2",
            document_type="pdf",
            chunk_type=ChunkType.IMAGE,
        ),
    )

    formatted = ContextBuilder.build_context([text_chunk, img_chunk])
    assert "[Context 1] [TEXT]" in formatted
    assert "Page: 1" in formatted
    assert "[Context 2] [IMAGE]" in formatted
    assert "Page: 3" in formatted


def test_multimodal_ingestion_pipeline_end_to_end(tmp_path: Path) -> None:
    """MultimodalIngestionPipeline should process text pages, images, and tables into DocumentChunk objects."""
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"dummy pdf content")

    mock_loader = MagicMock()
    mock_loader.extract.return_value = ExtractedPdfDocument(
        source_file="sample.pdf",
        file_path=pdf_path,
        document_type="pdf",
        pages=[
            ExtractedPage(
                page_number=1, content="Executive Summary text content of the report."
            ),
        ],
    )

    mock_img_extractor = MagicMock()
    img_path = tmp_path / "img1.png"
    img_path.write_bytes(b"fake image bytes")
    mock_img_extractor.extract_images.return_value = [
        DocumentAsset(
            asset_type=ChunkType.IMAGE,
            page_number=2,
            content="[Embedded Image Page 2]",
            source_file="sample.pdf",
            document_name="sample.pdf",
            username="admin",
            image_path=str(img_path),
            image_hash="hash1",
        )
    ]

    mock_table_extractor = MagicMock()
    mock_table_extractor.extract_tables.return_value = [
        DocumentAsset(
            asset_type=ChunkType.TABLE,
            page_number=3,
            content="| Header |\n| Data |",
            source_file="sample.pdf",
            document_name="sample.pdf",
            username="admin",
            table_markdown="| Header |\n| Data |",
            table_json='[{"Header": "Data"}]',
        )
    ]

    mock_ocr = MagicMock()
    mock_ocr.process_scanned_page.return_value = None
    mock_vision = MagicMock()
    mock_vision.generate_caption.return_value = "System Architecture Diagram"

    pipeline = MultimodalIngestionPipeline(
        pdf_loader=mock_loader,
        image_extractor=mock_img_extractor,
        table_extractor=mock_table_extractor,
        ocr_service=mock_ocr,
        vision_service=mock_vision,
    )

    _extracted_doc, chunks = pipeline.process_document(pdf_path, username="admin")

    assert len(chunks) >= 3
    chunk_types = [c.metadata.chunk_type for c in chunks]
    assert ChunkType.OCR in chunk_types
    assert ChunkType.IMAGE in chunk_types
    assert ChunkType.TABLE in chunk_types


def test_bm25_index_manager_load_preserves_corpus_and_returns_hits(
    tmp_path: Path,
) -> None:
    """Regression Test: BM25IndexManager.load() must load corpus before adding or searching."""
    from app.retrieval.bm25_index_manager import BM25IndexManager

    bm25_1 = BM25IndexManager(username="testuser", storage_dir=tmp_path)
    bm25_1.load()
    chunk1 = DocumentChunk(
        content="Microservices architecture design document",
        metadata=ChunkMetadata(
            source_file="doc1.pdf",
            page_number=1,
            chunk_id="c1",
            document_type="pdf",
        ),
    )
    bm25_1.add_documents([chunk1])

    # Second upload instance loads existing corpus before adding new chunk
    bm25_2 = BM25IndexManager(username="testuser", storage_dir=tmp_path)
    bm25_2.load()
    chunk2 = DocumentChunk(
        content="Database performance tuning guide",
        metadata=ChunkMetadata(
            source_file="doc2.pdf",
            page_number=1,
            chunk_id="c2",
            document_type="pdf",
        ),
    )
    bm25_2.add_documents([chunk2])

    # Confirm BOTH documents exist in corpus and return hits
    results = bm25_2.search("microservices", top_k=5)
    assert len(results) >= 1
    assert results[0].metadata.chunk_id == "c1"


def test_retrieval_service_parse_query_results_preserves_chunk_type_and_image_path() -> (
    None
):
    """Regression Test: _parse_query_results must preserve chunk_type and image_path metadata."""
    from app.retrieval.retrieval_engine import RetrievalEngine, RetrievalService

    raw_chroma_output = {
        "ids": [["doc_p3_image_0"]],
        "documents": [["[Image Caption Page 3]: System Architecture Diagram"]],
        "metadatas": [
            [
                {
                    "source_file": "architecture.pdf",
                    "page_number": 3,
                    "chunk_id": "doc_p3_image_0",
                    "document_type": "pdf",
                    "chunk_type": "image",
                    "document_name": "architecture.pdf",
                    "username": "admin",
                    "image_path": "/data/images/page_3_img_1.png",
                    "image_hash": "hash_abc123",
                }
            ]
        ],
    }

    parsed = RetrievalService._parse_query_results(raw_chroma_output)
    assert len(parsed) == 1
    chunk = parsed[0]
    assert chunk.metadata.chunk_type == ChunkType.IMAGE
    assert chunk.metadata.image_path == "/data/images/page_3_img_1.png"
    assert chunk.metadata.image_hash == "hash_abc123"
