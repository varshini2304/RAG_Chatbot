"""Service coordinating full re-extraction, re-chunking, and re-indexing for migrations."""

from __future__ import annotations

import logging
from typing import Any

import chromadb

from sentence_transformers import SentenceTransformer

from app.config import settings
from app.embeddings.embedding_pipeline import EmbeddingPipeline
from app.ingestion.image_ingestion import ImageIngestion, ImageIngestionService
from app.ingestion.multimodal_pipeline import MultimodalIngestionPipeline
from app.ingestion.upload_pipeline import UploadPipeline
from app.retrieval.bm25_index_manager import BM25IndexManager
from app.services.upload_service import UploadService
from app.services.workspace_service import WorkspaceService
from app.vectorstore.chroma_manager import ChromaVectorStore

LOGGER = logging.getLogger(__name__)

# Re-export for test patching compatibility
__all__ = ["IndexMaintenanceService", "SentenceTransformer"]


class IndexMaintenanceService:
    """Service to orchestrate index rebuilds and upgrades without requiring manual re-upload."""

    @classmethod
    def rebuild_indexes(
        cls,
        username: str,
        bm25_index_manager: BM25IndexManager | None = None,
    ) -> dict[str, Any]:
     
        user_dir = WorkspaceService.get_upload_directory(username)
        LOGGER.info(
            "Starting index rebuild for user %s at upload path: %s", username, user_dir
        )

        # 1. Read files already ingested
        files_to_rebuild = []
        if user_dir.exists():
            for file_path in user_dir.iterdir():
                if file_path.name == "hashes.json" or file_path.is_dir():
                    continue
                if (
                    file_path.suffix.lower().lstrip(".")
                    in settings.allowed_upload_extensions
                ):
                    files_to_rebuild.append(file_path)

        default_collection_name = WorkspaceService.get_collection_name(username)
        collection_name = settings.chroma_collection_name
        if collection_name == "internal_document_chunks_multilingual_v1":
            # Use default (setting is unchanged), so use workspace-based name for multi-user support
            collection_name = default_collection_name

        try:
            from chromadb.config import Settings as ChromaSettings

            client = chromadb.PersistentClient(
                path=str(settings.chroma_db_dir),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            client.delete_collection(name=collection_name)
            LOGGER.info("Deleted stale Chroma collection: %s", collection_name)
        except Exception as exc:
            LOGGER.debug("Chroma collection delete skipped (might not exist): %s", exc)

        store = ChromaVectorStore(collection_name=collection_name)

        # 3. Re-initialize BM25 index
        if bm25_index_manager is None:
            bm25_index_manager = BM25IndexManager(username)
        bm25_index_manager.clear()

        processed_docs = []
        total_chunks = 0
        failed_files = []

        pipeline = UploadPipeline(upload_dir=user_dir)

        # Lazy load model for embedding pipeline
        try:
            from app.embeddings.embedding_engine import EmbeddingEngine, EmbeddingService

            model = EmbeddingEngine._load_model(settings.embedding_model_name)
            emb_service = EmbeddingEngine(model=model)
            emb_pipeline = EmbeddingPipeline(
                embedding_service=emb_service, vector_store=store
            )
        except Exception as exc:
            LOGGER.exception("Failed to initialize embedding model for rebuild:")
            return {
                "processed_documents": [],
                "total_chunks": 0,
                "failed_files": [
                    (f.name, f"Embedding init failure: {exc}") for f in files_to_rebuild
                ],
            }

        # 4. Extract, chunk, embed, and index each document
        for file_path in files_to_rebuild:
            filename = file_path.name
            try:
                ext = file_path.suffix.lower().lstrip(".")
                LOGGER.info("Rebuilding document with fresh extraction: %s", filename)
                if ext in settings.image_extensions:
                    extracted_doc, chunks = ImageIngestionService().process_image_file(
                        file_path,
                        username=username,
                        refresh_caption=True,
                    )
                elif ext == "pdf":
                    (
                        extracted_doc,
                        chunks,
                    ) = MultimodalIngestionPipeline().process_document(
                        file_path,
                        username=username,
                        refresh_image_captions=True,
                    )
                else:
                    extracted_doc = pipeline._extract(file_path)
                    chunks = UploadService.chunk_document(extracted_doc)

                if chunks:
                    LOGGER.info(
                        "Re-embedding and indexing %s chunks for: %s",
                        len(chunks),
                        filename,
                    )
                    # Re-embed and index in Chroma
                    emb_pipeline.run(chunks)

                    bm25_index_manager.add_documents(chunks)

                    processed_docs.append(filename)
                    total_chunks += len(chunks)
                else:
                    failed_files.append((filename, "No chunks generated"))
            except Exception as exc:
                LOGGER.exception("Failed to rebuild document %s", filename)
                failed_files.append((filename, str(exc)))

        LOGGER.info(
            "Completed index rebuild for user %s: processed=%s failed=%s",
            username,
            len(processed_docs),
            len(failed_files),
        )
        return {
            "processed_documents": processed_docs,
            "total_chunks": total_chunks,
            "failed_files": failed_files,
        }
