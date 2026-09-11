from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from app.config import settings
from app.ingestion.chunker import DocumentChunker
from app.ingestion.image_extractor import ImageExtractor
from app.ingestion.pdf_loader import PDFLoader
from app.models.schemas import (
    ChunkMetadata,
    ChunkType,
    DocumentAsset,
    DocumentChunk,
    ExtractedPage,
    ExtractedPdfDocument,
)
from app.ingestion.table_extractor import TableExtractor
from app.ocr.ocr_engine import OCREngine, OCRService
from app.vision.vision_engine import VisionEngine, VisionService

LOGGER = logging.getLogger(__name__)


class MultimodalIngestionPipeline:

    def __init__(
        self,
        pdf_loader: PDFLoader | None = None,
        image_extractor: ImageExtractor | None = None,
        table_extractor: TableExtractor | None = None,
        ocr_service: OCRService | None = None,
        vision_service: VisionService | None = None,
        chunker: DocumentChunker | None = None,
    ) -> None:
        self.pdf_loader = pdf_loader or PDFLoader()
        self.image_extractor = image_extractor or ImageExtractor()
        self.table_extractor = table_extractor or TableExtractor()
        self.ocr_service = ocr_service or OCRService()
        self.vision_service = vision_service or VisionService()
        self.chunker = chunker or DocumentChunker()

    def process_document(
        self,
        file_path: Path,
        username: str = "default",
        progress_callback: Callable[[str], None] | None = None,
        refresh_image_captions: bool = False,
    ) -> tuple[ExtractedPdfDocument, list[DocumentChunk]]:
        """Process document through full multimodal ingestion workflow."""
        doc_name = file_path.name
        LOGGER.info("Starting multimodal pipeline for %s (user=%s)", doc_name, username)

        # 1. Extract Text
        if progress_callback:
            progress_callback("Extracting text...")
        extracted_doc = self.pdf_loader.extract(file_path)

        all_assets: list[DocumentAsset] = []

        # Convert text pages to assets; track low-text or image-bearing pages for OCR
        scanned_page_numbers: list[int] = []
        for page in extracted_doc.pages:
            content = page.content.strip()
            if len(content) < settings.ocr_scanned_page_threshold:
                scanned_page_numbers.append(page.page_number)
            all_assets.append(
                DocumentAsset(
                    asset_type=ChunkType.TEXT if len(content) >= 50 else ChunkType.OCR,
                    page_number=page.page_number,
                    content=(
                        content
                        if len(content) >= 50
                        else f"[Scanned Page {page.page_number}]"
                    ),
                    source_file=doc_name,
                    document_name=doc_name,
                    username=username,
                )
            )

        # 2. Extract Images & Diagrams
        if progress_callback:
            progress_callback("Extracting images...")
        image_assets = self.image_extractor.extract_images(
            file_path, username=username, document_name=doc_name
        )
        # Note: raw image_assets are kept for OCR page checking and vision captioning below;
        # only the captioned version in Step 5 is appended to all_assets to avoid duplicates.

        # Include pages containing extracted images in OCR scanning
        for img_asset in image_assets:
            if img_asset.page_number not in scanned_page_numbers:
                scanned_page_numbers.append(img_asset.page_number)

        # 3. OCR Support for Scanned & Graphic Pages
        if scanned_page_numbers:
            if progress_callback:
                progress_callback("Running OCR...")
            for page_num in sorted(set(scanned_page_numbers)):
                try:
                    ocr_asset = self.ocr_service.process_scanned_page(
                        file_path, page_num, username=username, document_name=doc_name
                    )
                    if ocr_asset:
                        all_assets.append(ocr_asset)
                except Exception as exc:
                    LOGGER.warning(
                        "OCR processing failed for page %s: %s", page_num, exc
                    )

        # 4. Table Extraction
        if progress_callback:
            progress_callback("Extracting tables...")
        table_assets = self.table_extractor.extract_tables(
            file_path, username=username, document_name=doc_name
        )
        all_assets.extend(table_assets)

        # 5. Vision Captioning for Images
        if image_assets:
            if progress_callback:
                progress_callback("Generating image captions...")
            for img_asset in image_assets:
                if img_asset.image_path:
                    try:
                        if refresh_image_captions:
                            caption = self.vision_service.generate_caption(
                                img_asset.image_path,
                                img_asset.image_hash,
                                force_refresh=True,
                            )
                        else:
                            caption = self.vision_service.generate_caption(
                                img_asset.image_path,
                                img_asset.image_hash,
                            )
                        caption_text = (
                            f"[Image Caption Page {img_asset.page_number}]: {caption}\n"
                            f"Figure Context: {img_asset.content}"
                        )
                        all_assets.append(
                            DocumentAsset(
                                asset_type=ChunkType.IMAGE,
                                page_number=img_asset.page_number,
                                content=caption_text,
                                source_file=doc_name,
                                document_name=doc_name,
                                username=username,
                                image_path=img_asset.image_path,
                                image_hash=img_asset.image_hash,
                            )
                        )
                    except Exception as caption_exc:
                        LOGGER.warning(
                            "Vision caption generation failed for %s: %s",
                            img_asset.image_path,
                            caption_exc,
                        )

        # Update assets list on document
        extracted_doc.assets = all_assets

        # 6. Generate Multimodal Chunks
        if progress_callback:
            progress_callback("Generating embeddings...")
        chunks: list[DocumentChunk] = []
        for idx, asset in enumerate(all_assets, start=1):
            if asset.asset_type == ChunkType.TEXT:
                # Use standard recursive chunking for long body text
                page_doc = ExtractedPdfDocument(
                    source_file=doc_name,
                    file_path=file_path,
                    pages=[
                        ExtractedPage(
                            page_number=asset.page_number, content=asset.content
                        )
                    ],
                )
                text_chunks = self.chunker.chunk_document(page_doc)
                chunks.extend(text_chunks)
            else:
                # Multimodal asset chunk (Image caption, Table, OCR)
                chunk_id = (
                    f"{doc_name}_p{asset.page_number}_{asset.asset_type.value}_{idx}"
                )
                metadata = ChunkMetadata(
                    source_file=doc_name,
                    page_number=asset.page_number,
                    chunk_id=chunk_id,
                    document_type="pdf",
                    chunk_type=asset.asset_type,
                    document_name=doc_name,
                    username=username,
                    image_path=asset.image_path,
                    image_hash=asset.image_hash,
                    table_markdown=asset.table_markdown,
                    table_json=asset.table_json,
                    ocr_engine=asset.ocr_engine,
                    ocr_confidence=asset.ocr_confidence,
                    ocr_processing_time_ms=asset.ocr_processing_time_ms,
                )
                chunk = DocumentChunk(content=asset.content, metadata=metadata)
                chunks.append(chunk)

        counts: dict[str, int] = {}
        for c in chunks:
            ctype = getattr(c.metadata, "chunk_type", "text")
            cstr = str(getattr(ctype, "value", ctype)).lower()
            counts[cstr] = counts.get(cstr, 0) + 1

        LOGGER.info(
            "MULTIMODAL EXTRACTION COMPLETED FOR %s: %d total chunks (Text: %d, Image/Diagram: %d, Table: %d, OCR: %d)",
            doc_name,
            len(chunks),
            counts.get("text", 0),
            counts.get("image", 0) + counts.get("diagram", 0),
            counts.get("table", 0) + counts.get("chart", 0),
            counts.get("ocr", 0),
        )
        return extracted_doc, chunks
