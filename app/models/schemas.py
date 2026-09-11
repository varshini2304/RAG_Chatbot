"""Typed data models for the Day 1 PDF upload and extraction workflow."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ExtractedPage(BaseModel):
    """Represents text extracted from a single PDF page."""

    model_config = ConfigDict(frozen=True)

    page_number: int = Field(ge=1)
    content: str = Field(min_length=1)

    @property
    def metadata(self) -> "ExtractedPage":
        """Expose page metadata for callers that use the older nested access."""
        return self


class ExtractedPdfDocument(BaseModel):
    """Container for a saved PDF and its extracted page content."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    source_file: str
    file_path: Path
    document_type: str = "pdf"
    pages: list[ExtractedPage]

    @property
    def page_count(self) -> int:
        """Return the number of extracted pages."""
        return len(self.pages)

    @property
    def total_characters(self) -> int:
        """Return the total extracted character count across pages."""
        return sum(len(page.content) for page in self.pages)
