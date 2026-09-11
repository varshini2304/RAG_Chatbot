"""Recursive character-based chunking and metadata validation."""

from __future__ import annotations

import logging
from typing import Any

try:
    from langchain_text_splitters import (
        RecursiveCharacterTextSplitter,
    )  # type: ignore[import-untyped]
except ImportError:

    class RecursiveCharacterTextSplitter:  # type: ignore[no-redef] # pyright: ignore[reportRedeclaration]
        def __init__(
            self,
            chunk_size: int = 800,
            chunk_overlap: int = 120,
            length_function: Any = len,
            separators: list[str] | None = None,
            keep_separator: bool = True,
            **kwargs: Any,
        ) -> None:
            self.chunk_size = chunk_size
            self.chunk_overlap = chunk_overlap
            self.keep_separator = keep_separator

        def split_text(self, text: str) -> list[str]:
            chunks = []
            start = 0
            while start < len(text):
                end = start + self.chunk_size
                chunks.append(text[start:end])
                start += self.chunk_size - self.chunk_overlap
            return [c for c in chunks if c.strip()]


from pydantic import ValidationError

from app.config import settings
from app.ingestion.exceptions import ChunkingError, MetadataValidationError
from app.models.schemas import ChunkMetadata, DocumentChunk, ExtractedPdfDocument

LOGGER = logging.getLogger(__name__)

MULTILINGUAL_SEPARATORS = [
    "\n\n",
    "\n",
    "。",
    "．",
    ". ",
    ".",
    "！",
    "!",
    "？",
    "?",
    "；",
    ";",
    "、",
    "，",
    ",",
    " ",
    "\u3000",
    "\u200b",
    "",
]


class DocumentChunker:
    """Generate semantic chunks from extracted page content."""

    def __init__(
        self, chunk_size: int | None = None, chunk_overlap: int | None = None
    ) -> None:
        """Initialize the text splitter with configured chunk parameters."""
        self._chunk_size = chunk_size if chunk_size is not None else settings.chunk_size
        self._chunk_overlap = (
            chunk_overlap if chunk_overlap is not None else settings.chunk_overlap
        )

        if self._chunk_size <= 0:
            raise ChunkingError("Chunk size must be greater than zero.")
        if self._chunk_overlap < 0:
            raise ChunkingError("Chunk overlap cannot be negative.")
        if self._chunk_overlap >= self._chunk_size:
            raise ChunkingError("Chunk overlap must be smaller than chunk size.")

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self._chunk_size,
            chunk_overlap=self._chunk_overlap,
            separators=MULTILINGUAL_SEPARATORS,
            keep_separator=True,
        )

    def chunk_document(
        self, extracted_document: ExtractedPdfDocument
    ) -> list[DocumentChunk]:
        """Split an extracted document into semantic text chunks."""
        LOGGER.info(
            "Starting chunk generation for %s with %s extracted pages",
            extracted_document.source_file,
            extracted_document.page_count,
        )

        if not extracted_document.pages:
            raise ChunkingError("Cannot chunk a document with no extracted pages.")

        chunks: list[DocumentChunk] = []
        for page in extracted_document.pages:
            self._validate_document_context(extracted_document, page.page_number)
            page_chunks = self._splitter.split_text(page.content)
            if page_chunks:
                punctuation_separators = {
                    "。",
                    "．",
                    ".",
                    "！",
                    "!",
                    "？",
                    "?",
                    "；",
                    ";",
                    "、",
                    "，",
                    ",",
                }
                processed_chunks: list[str] = []
                for text in page_chunks:
                    stripped_leading = ""
                    while text and text[0] in punctuation_separators:
                        stripped_leading += text[0]
                        text = text[1:]
                    if stripped_leading and processed_chunks:
                        processed_chunks[-1] += stripped_leading
                    processed_chunks.append(text)
                page_chunks = [t.strip() for t in processed_chunks if t.strip()]

            if not page_chunks:
                LOGGER.warning(
                    "No chunks generated for %s page %s",
                    extracted_document.source_file,
                    page.page_number,
                )
                continue

            for chunk_index, chunk_text in enumerate(page_chunks, start=1):
                chunk_id = self._build_chunk_id(
                    extracted_document.source_file,
                    page.page_number,
                    chunk_index,
                )
                if not chunk_id or not chunk_id.strip():
                    LOGGER.error(
                        "Chunk metadata generation failed for %s page %s chunk %s: empty chunk_id",
                        extracted_document.source_file,
                        page.page_number,
                        chunk_index,
                    )
                    raise MetadataValidationError(
                        "Chunk metadata validation failed: empty chunk_id."
                    )
                try:
                    metadata = ChunkMetadata(
                        source_file=extracted_document.source_file,
                        page_number=page.page_number,
                        chunk_id=chunk_id,
                        document_type=extracted_document.document_type,
                    )
                except ValidationError as exc:
                    LOGGER.error(
                        "Chunk metadata generation failed for %s page %s chunk %s: %s",
                        extracted_document.source_file,
                        page.page_number,
                        chunk_index,
                        exc,
                    )
                    raise MetadataValidationError(
                        "Chunk metadata validation failed during metadata generation."
                    ) from exc
                self._validate_chunk_metadata(metadata)
                chunk = DocumentChunk(content=chunk_text, metadata=metadata)
                chunks.append(chunk)
                LOGGER.info(
                    "Created chunk %s for %s page %s",
                    metadata.chunk_id,
                    metadata.source_file,
                    metadata.page_number,
                )

        if not chunks:
            raise ChunkingError(
                f"No chunks could be generated for {extracted_document.source_file}."
            )

        self._validate_chunk_collection(chunks)
        LOGGER.info(
            "Chunking completed for %s with %s generated chunks",
            extracted_document.source_file,
            len(chunks),
        )
        return chunks

    @staticmethod
    def _build_chunk_id(source_file: str, page_number: int, chunk_index: int) -> str:
        """Build a stable chunk identifier from file, page, and index."""
        return f"{source_file}-p{page_number}-c{chunk_index}"

    @staticmethod
    def _validate_document_context(
        extracted_document: ExtractedPdfDocument, page_number: int
    ) -> None:
        """Validate document-level metadata required for chunk generation."""
        if (
            not extracted_document.source_file
            or not extracted_document.source_file.strip()
        ):
            raise MetadataValidationError(
                "Chunk metadata validation failed: missing source_file."
            )
        if page_number < 1:
            raise MetadataValidationError(
                "Chunk metadata validation failed: invalid page_number."
            )
        if (
            not extracted_document.document_type
            or not extracted_document.document_type.strip()
        ):
            raise MetadataValidationError(
                "Chunk metadata validation failed: missing document_type."
            )

    @staticmethod
    def _validate_chunk_metadata(metadata: ChunkMetadata) -> None:
        """Validate metadata attached to one generated chunk."""
        if not metadata.source_file.strip():
            raise MetadataValidationError(
                "Chunk metadata validation failed: missing source_file."
            )
        if metadata.page_number < 1:
            raise MetadataValidationError(
                "Chunk metadata validation failed: invalid page_number."
            )
        if not metadata.chunk_id.strip():
            raise MetadataValidationError(
                "Chunk metadata validation failed: empty chunk_id."
            )
        if not metadata.document_type.strip():
            raise MetadataValidationError(
                "Chunk metadata validation failed: missing document_type."
            )
        LOGGER.info(
            "Validated metadata for chunk %s (%s page %s)",
            metadata.chunk_id,
            metadata.source_file,
            metadata.page_number,
        )

    @staticmethod
    def _validate_chunk_collection(chunks: list[DocumentChunk]) -> None:
        """Validate ordering, page association, and chunk id uniqueness."""
        seen_chunk_ids: set[str] = set()
        previous_page_number = -1

        for index, chunk in enumerate(chunks):
            metadata = chunk.metadata
            if metadata.chunk_id in seen_chunk_ids:
                LOGGER.error("Duplicate chunk_id detected: %s", metadata.chunk_id)
                raise MetadataValidationError(
                    f"Chunk metadata validation failed: duplicate chunk_id {metadata.chunk_id}."
                )
            seen_chunk_ids.add(metadata.chunk_id)

            if metadata.page_number < previous_page_number:
                LOGGER.error(
                    "Chunk ordering invalid: page %s appeared after page %s",
                    metadata.page_number,
                    previous_page_number,
                )
                raise ChunkingError("Chunk ordering validation failed.")

            if index > 0:
                previous_chunk = chunks[index - 1]
                if metadata.page_number == previous_chunk.metadata.page_number:
                    current_index = int(metadata.chunk_id.rsplit("-c", maxsplit=1)[1])
                    previous_index = int(
                        previous_chunk.metadata.chunk_id.rsplit("-c", maxsplit=1)[1]
                    )
                    if current_index <= previous_index:
                        LOGGER.error(
                            "Chunk ordering invalid within page %s for chunk_id %s",
                            metadata.page_number,
                            metadata.chunk_id,
                        )
                        raise ChunkingError("Chunk ordering validation failed.")

            previous_page_number = metadata.page_number
