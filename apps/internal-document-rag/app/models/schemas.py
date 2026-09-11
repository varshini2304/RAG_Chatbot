"""Typed data models for extraction, chunking, and retrieval workflows."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChunkType(str, Enum):
    """Supported multimodal chunk types."""

    TEXT = "text"
    IMAGE = "image"
    TABLE = "table"
    OCR = "ocr"
    DIAGRAM = "diagram"
    CHART = "chart"


class DocumentAsset(BaseModel):
    """Intermediate model for extracted raw assets prior to chunking."""

    model_config = ConfigDict(frozen=True)

    asset_type: ChunkType
    page_number: int = Field(ge=1)
    content: str = Field(min_length=1)
    source_file: str = Field(min_length=1)
    document_name: str = ""
    username: str = ""
    image_path: str | None = None
    image_hash: str | None = None
    image_dimensions: tuple[int, int] | None = None
    table_markdown: str | None = None
    table_json: str | None = None
    ocr_engine: str | None = None
    ocr_confidence: float | None = None
    ocr_processing_time_ms: float | None = None


class ExtractedPage(BaseModel):
    """Represents text extracted from a single PDF page."""

    model_config = ConfigDict(frozen=True)

    page_number: int = Field(ge=1)
    content: str = Field(min_length=1)

    @property
    def metadata(self) -> ExtractedPage:
        """Expose page metadata for callers that use the older nested access."""
        return self


class ExtractedPdfDocument(BaseModel):
    """Container for a saved document (PDF or TXT) and its extracted page content."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    source_file: str
    file_path: Path
    document_type: str = "pdf"
    pages: list[ExtractedPage]
    assets: list[DocumentAsset] = Field(default_factory=list)

    @property
    def page_count(self) -> int:
        """Return the number of extracted pages."""
        return len(self.pages)

    @property
    def total_characters(self) -> int:
        """Return the total extracted character count across pages."""
        return sum(len(page.content) for page in self.pages)


class ChunkMetadata(BaseModel):
    """Metadata preserved for each generated chunk."""

    model_config = ConfigDict(frozen=True, use_enum_values=True)

    source_file: str = Field(min_length=1)
    page_number: int = Field(ge=1)
    chunk_id: str = Field(min_length=1)
    document_type: str = Field(min_length=1)
    chunk_type: ChunkType = Field(default=ChunkType.TEXT)
    document_name: str = ""
    username: str = ""
    image_path: str | None = None
    image_hash: str | None = None
    table_markdown: str | None = None
    table_json: str | None = None
    ocr_engine: str | None = None
    ocr_confidence: float | None = None
    ocr_processing_time_ms: float | None = None

    def to_chroma_dict(self) -> dict[str, str | int | float | bool]:
        """Convert metadata to a clean ChromaDB primitive dictionary without None or Enum objects."""
        data = self.model_dump(mode="json", exclude_none=True)
        res: dict[str, str | int | float | bool] = {}
        for k, v in data.items():
            if isinstance(v, (str, int, float, bool)):
                res[k] = v
            else:
                res[k] = str(v)
        return res


class DocumentChunk(BaseModel):
    """Represents a semantic chunk generated from extracted page text or multimodal assets."""

    model_config = ConfigDict(frozen=True)

    content: str = Field(min_length=1)
    metadata: ChunkMetadata


class RetrievalResult(BaseModel):
    """A single chunk returned by similarity search with its relevance score."""

    model_config = ConfigDict(frozen=True)

    content: str = Field(min_length=1)
    metadata: ChunkMetadata
    score: float = Field(ge=0.0)


# ---------------------------------------------------------------------------
# Step 6 – Top-K Retrieval configuration
# ---------------------------------------------------------------------------

#: Maximum allowed value for top_k to prevent runaway queries.
TOP_K_MAX: int = 100


class InvalidTopKError(ValueError):
    """Raised when a top_k value fails validation.

    Using ``ValueError`` as the base makes it compatible with Pydantic's
    ``field_validator`` mechanism as well as manual validation paths.
    """


class TopKRetrievalConfig(BaseModel):


    model_config = ConfigDict(frozen=True)

    top_k: int = Field(default=5, ge=1)

    @field_validator("top_k", mode="after")
    @classmethod
    def _validate_top_k_upper_bound(cls, value: int) -> int:
        """Reject top_k values that exceed the hard upper limit."""
        if value > TOP_K_MAX:
            raise InvalidTopKError(
                f"top_k={value} exceeds the maximum allowed value of {TOP_K_MAX}."
            )
        return value
