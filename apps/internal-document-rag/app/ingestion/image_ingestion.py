"""Ingestion service for standalone image file uploads (PNG / JPG / WEBP / TIFF / BMP).

When a user uploads a raw image instead of a PDF, this service:
1. Saves the file to the user's upload directory.
2. Computes a SHA-256 hash for cache-based deduplication.
3. Calls VisionEngine to generate a rich caption (Gemini Vision -> Ollama Vision -> fallback).
4. Wraps the caption into a single DocumentChunk (ChunkType.IMAGE) and an ExtractedPdfDocument
   so that the rest of the upload pipeline (embed_and_index, BM25, ChromaDB) requires no changes.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from app.config import settings
from app.models.schemas import (
    ChunkMetadata,
    ChunkType,
    DocumentChunk,
    ExtractedPage,
    ExtractedPdfDocument,
)
from app.vision.vision_engine import VisionEngine, VisionService

LOGGER = logging.getLogger(__name__)

# Supported standalone image extensions (must match settings.image_extensions)
_SUPPORTED_IMAGE_EXTENSIONS = frozenset(settings.image_extensions)


class ImageIngestion:
    """Process a standalone image file upload and produce indexable DocumentChunk objects.

    This service follows the same interface contract as MultimodalIngestionPipeline
    so that UploadService can delegate to it without any structural changes.
    """

    def __init__(
        self,
        vision_service: VisionEngine | VisionService | None = None,
        upload_base_dir: Path | None = None,
    ) -> None:
        self.vision_service = vision_service or VisionEngine()
        self.upload_base_dir = upload_base_dir or settings.upload_dir

    def process_image_file(
        self,
        file_path: Path,
        username: str = "default",
        refresh_caption: bool = False,
    ) -> tuple[ExtractedPdfDocument, list[DocumentChunk]]:
        """Process a standalone image file and return (ExtractedPdfDocument, [DocumentChunk]).

        The returned ExtractedPdfDocument has a single dummy page whose content is the
        generated caption, making it compatible with downstream workspace loading logic.
        The DocumentChunk list contains one IMAGE chunk ready for vector + BM25 indexing.

        Args:
            file_path: Absolute path to the saved image file (already written to disk).
            username: Owner username used for metadata tagging.
            refresh_caption: If True, bypass caption cache.

        Returns:
            Tuple of (ExtractedPdfDocument, list[DocumentChunk]).
        """
        ext = file_path.suffix.lower().lstrip(".")
        if ext not in _SUPPORTED_IMAGE_EXTENSIONS:
            raise ValueError(
                f"Unsupported image extension '.{ext}'. "
                f"Supported: {sorted(_SUPPORTED_IMAGE_EXTENSIONS)}"
            )

        doc_name = file_path.name
        LOGGER.info(
            "Starting image ingestion for standalone image: %s (user=%s)",
            doc_name,
            username,
        )

        # Compute SHA-256 hash for cache dedup
        image_bytes = file_path.read_bytes()
        image_hash = hashlib.sha256(image_bytes).hexdigest()
        LOGGER.info(
            "IMAGE FILE | Name: %s | Size: %d bytes | SHA-256: %.12s",
            doc_name,
            len(image_bytes),
            image_hash,
        )

        # Generate caption via VisionService (Gemini -> Ollama -> fallback)
        caption = self.vision_service.generate_caption(
            file_path,
            image_hash=image_hash,
            force_refresh=refresh_caption,
        )
        LOGGER.info(
            "IMAGE CAPTION GENERATED | File: %s | Caption length: %d chars | Hash: %.12s",
            doc_name,
            len(caption),
            image_hash,
        )

        # Build a single-page ExtractedPdfDocument (required by workspace loader)
        extracted_doc = ExtractedPdfDocument(
            source_file=doc_name,
            file_path=file_path,
            document_type=ext,
            pages=[ExtractedPage(page_number=1, content=caption)],
        )

        # Build the single IMAGE DocumentChunk
        chunk_id = f"{doc_name}_p1_image_1"
        metadata = ChunkMetadata(
            source_file=doc_name,
            page_number=1,
            chunk_id=chunk_id,
            document_type=ext,
            chunk_type=ChunkType.IMAGE,
            document_name=doc_name,
            username=username,
            image_path=str(file_path),
            image_hash=image_hash,
        )
        chunk = DocumentChunk(content=caption, metadata=metadata)

        LOGGER.info(
            "IMAGE INGESTION COMPLETED | %s: 1 chunk (Image/Caption) | User: %s",
            doc_name,
            username,
        )
        return extracted_doc, [chunk]


# ---------------------------------------------------------------------------
# Backwards-compatibility alias — ImageIngestionService maps to ImageIngestion.
# ---------------------------------------------------------------------------
ImageIngestionService = ImageIngestion
