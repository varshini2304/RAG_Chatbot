
from __future__ import annotations

import logging

import streamlit as st

from app.ingestion.exceptions import ExtractionError, FileValidationError
from app.ingestion.upload_pipeline import UploadPipeline
from app.models.schemas import ExtractedPdfDocument

LOGGER = logging.getLogger(__name__)


def render_upload_workspace() -> None:
    st.subheader("Document Upload")
    uploaded_files = st.file_uploader(
        "Upload PDF documents",
        type=["pdf"],
        accept_multiple_files=True,
        help="Supported file type: PDF. You can upload more than one file.",
    )

    if not uploaded_files:
        st.info("Upload one or more PDF files to extract and review page-level text.")
        return

    pipeline = UploadPipeline()
    try:
        extracted_documents = pipeline.process_uploads(uploaded_files)
    except FileValidationError as exc:
        LOGGER.warning("Upload validation failed: %s", exc)
        st.error(str(exc))
        return
    except ExtractionError as exc:
        LOGGER.warning("Extraction failed: %s", exc)
        st.error(str(exc))
        return
    except OSError as exc:
        LOGGER.exception("Unexpected file system error during upload")
        st.error(f"Unable to persist the uploaded file: {exc}")
        return

    st.success(f"{len(extracted_documents)} document(s) uploaded and extracted successfully.")
    for extracted_document in extracted_documents:
        _render_extraction_summary(extracted_document)


def _render_extraction_summary(extracted_document: ExtractedPdfDocument) -> None:
    st.markdown(f"### {extracted_document.source_file}")
    col1, col2, col3 = st.columns(3)
    col1.metric("Source File", extracted_document.source_file)
    col2.metric("Pages Extracted", extracted_document.page_count)
    col3.metric("Characters", extracted_document.total_characters)

    for page in extracted_document.pages:
        with st.expander(
            f"{extracted_document.source_file} - Page {page.page_number}",
            expanded=False,
        ):
            st.text(page.content)
