"""Service layer coordinating document validation, text extraction, chunking, and indexing steps."""

from __future__ import annotations

import logging
from typing import Any

from app.config import settings
from app.embeddings.embedding_engine import EmbeddingEngine, EmbeddingService
from app.embeddings.embedding_pipeline import EmbeddingPipeline
from app.ingestion.chunker import DocumentChunker
from app.ingestion.multimodal_pipeline import MultimodalIngestionPipeline
from app.ingestion.upload_pipeline import UploadPipeline
from app.models.schemas import DocumentChunk, ExtractedPdfDocument
from app.services.workspace_service import WorkspaceService

LOGGER = logging.getLogger(__name__)


class UploadService:
    """Synchronous file processing coordinators, execution-strategy independent."""

    @classmethod
    def extract_document(
        cls, username: str, uploaded_file: Any
    ) -> ExtractedPdfDocument:
        filename = uploaded_file.name
        WorkspaceService.prepare_document_upload(username, filename)

        user_dir = WorkspaceService.get_upload_directory(username)
        pipeline = UploadPipeline(upload_dir=user_dir)

        sanitized_name = pipeline._sanitize_filename(uploaded_file.name)
        pipeline._validate_upload(uploaded_file, sanitized_name)
        saved_path = pipeline._save_upload(uploaded_file, sanitized_name)

        ext = saved_path.suffix.lower().lstrip(".")

        if ext in settings.image_extensions:
            from app.ingestion.image_ingestion import ImageIngestion

            image_svc = ImageIngestion()
            extracted_doc, chunks = image_svc.process_image_file(
                saved_path, username=username
            )
            extracted_doc._pregenerated_chunks = chunks
            return extracted_doc

        # Route PDFs through the full multimodal pipeline
        if ext == "pdf":
            multimodal_pipe = MultimodalIngestionPipeline()
            extracted_doc, chunks = multimodal_pipe.process_document(
                saved_path, username=username
            )
            extracted_doc._pregenerated_chunks = chunks
            return extracted_doc

        return pipeline._extract(saved_path)

    @classmethod
    def chunk_document(cls, document: ExtractedPdfDocument) -> list[DocumentChunk]:
        """Run text splitter or return pregenerated multimodal chunks."""
        pregenerated = getattr(document, "_pregenerated_chunks", None)
        if pregenerated:
            return pregenerated

        chunker = DocumentChunker()
        return chunker.chunk_document(document)

    @classmethod
    def embed_and_index(
        cls,
        chunks: list[DocumentChunk],
        embedding_model: Any,
        vector_store: Any,
    ) -> list[str]:
        """Generate dense vectors for chunks and index them inside the vector store and BM25 index."""
        service = EmbeddingService(model=embedding_model)
        pipeline = EmbeddingPipeline(
            embedding_service=service, vector_store=vector_store
        )
        inserted_ids = pipeline.run(chunks)

        if chunks:
            try:
                username = getattr(chunks[0].metadata, "username", "admin") or "admin"
                from app.retrieval.bm25_index_manager import BM25IndexManager

                bm25 = BM25IndexManager(username=username)
                bm25.load()
                bm25.add_documents(chunks)
                LOGGER.info(
                    "INDEXING COMPLETED: Successfully indexed %d chunks into ChromaDB & BM25 for user '%s'",
                    len(inserted_ids),
                    username,
                )
            except Exception as exc:
                LOGGER.warning(
                    "Failed to sync BM25 index during embed_and_index: %s", exc
                )

        return inserted_ids
