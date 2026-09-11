from __future__ import annotations

import hashlib
import logging
from pathlib import Path

try:
    import fitz  # type: ignore[import-untyped]
except ImportError:
    fitz = None  # type: ignore

from app.config import settings
from app.ingestion.exceptions import ImageExtractionError
from app.models.schemas import ChunkType, DocumentAsset

LOGGER = logging.getLogger(__name__)


class ImageExtractor:
    """Extract page-by-page embedded images from PDF documents using PyMuPDF."""

    def __init__(self, images_base_dir: Path | None = None) -> None:
        self.images_base_dir = images_base_dir or (settings.data_dir / "images")

    def extract_images(
        self,
        pdf_path: Path,
        username: str = "default",
        document_name: str | None = None,
    ) -> list[DocumentAsset]:
        """Extract embedded images from a PDF file and return as DocumentAsset list."""
        doc_name = document_name or pdf_path.name
        LOGGER.info("Starting image extraction for %s (user=%s)", doc_name, username)

        if fitz is None:
            LOGGER.warning(
                "PyMuPDF (fitz) is not installed; skipping image extraction."
            )
            return []

        out_dir = self.images_base_dir / username / doc_name
        out_dir.mkdir(parents=True, exist_ok=True)

        assets: list[DocumentAsset] = []

        try:
            document = fitz.open(pdf_path)
        except Exception as exc:
            LOGGER.exception("Failed to open PDF for image extraction: %s", pdf_path)
            raise ImageExtractionError(
                f"Failed to open PDF for image extraction: {pdf_path.name}"
            ) from exc

        try:
            for page_idx in range(len(document)):
                page_index = page_idx + 1
                page = document[page_idx]
                image_list = page.get_images(full=True)
                for img_idx, img_info in enumerate(image_list, start=1):
                    xref = img_info[0]
                    try:
                        base_image = document.extract_image(xref)
                        if not base_image:
                            continue

                        image_bytes = base_image["image"]
                        ext = base_image["ext"]
                        width = base_image.get("width", 0)
                        height = base_image.get("height", 0)

                        # Filter out tiny icon images / logos (< 80x80 pixels)
                        if width < 80 or height < 80 or len(image_bytes) < 2048:
                            LOGGER.debug(
                                "Skipped small image on page %s (xref=%s): %dx%d px, %d bytes",
                                page_index,
                                xref,
                                width,
                                height,
                                len(image_bytes),
                            )
                            continue

                        img_hash = hashlib.sha256(image_bytes).hexdigest()
                        filename = (
                            f"page_{page_index}_img_{img_idx}_{img_hash[:8]}.{ext}"
                        )
                        img_path = out_dir / filename

                        # Detect duplicates — same SHA-256 already saved to disk
                        if img_path.exists():
                            LOGGER.info(
                                "DUPLICATE IMAGE DETECTED | Page: %s | Hash: %.12s | "
                                "File: %s — reusing cached file, skipping re-save.",
                                page_index,
                                img_hash,
                                filename,
                            )
                        else:
                            img_path.write_bytes(image_bytes)

                        LOGGER.info(
                            "IMAGE EXTRACTED | Page: %s | Format: %s | "
                            "Dimensions: %dx%d | Hash: %.12s | Path: %s",
                            page_index,
                            ext.upper(),
                            width,
                            height,
                            img_hash,
                            img_path,
                        )

                        page_text = str(page.get_text("text") or "").strip()
                        asset_content = (
                            f"[Embedded Image & Diagram on Page {page_index}]: {page_text}\n"
                            f"Image File: {filename}"
                            if page_text
                            else f"[Embedded Image on Page {page_index}: {filename}]"
                        )

                        asset = DocumentAsset(
                            asset_type=ChunkType.IMAGE,
                            page_number=page_index,
                            content=asset_content,
                            source_file=pdf_path.name,
                            document_name=doc_name,
                            username=username,
                            image_path=str(img_path),
                            image_hash=img_hash,
                            image_dimensions=(width, height),
                        )
                        assets.append(asset)
                    except Exception as img_exc:
                        LOGGER.warning(
                            "Failed to extract image xref %s on page %s of %s: %s",
                            xref,
                            page_index,
                            doc_name,
                            img_exc,
                        )
                        continue

            LOGGER.info("Extracted %s valid images from %s", len(assets), doc_name)
            return assets
        finally:
            document.close()
