"""Streamlit entry point for the Internal Document RAG Chatbot.

This module initializes the Step 2 application shell only. Future SDLC stages
will connect document ingestion, vector search, retrieval, and Gemini-backed
chatbot workflows.
"""

from __future__ import annotations

import streamlit as st

from app.config import settings


def render_banner() -> None:
    """Render the project banner for the Streamlit application shell."""
    st.title("Internal Document RAG Chatbot")
    st.caption(
        "Secure internal document question answering powered by LangChain, "
        "ChromaDB, Sentence Transformers, and Gemini."
    )


def render_upload_placeholder() -> None:
    """Render the future document upload area without processing files."""
    st.subheader("Document Upload")
    st.file_uploader(
        "Upload internal documents",
        type=["pdf", "txt", "md", "docx"],
        accept_multiple_files=True,
        disabled=True,
        help="Document ingestion will be implemented in a future SDLC step.",
    )


def main() -> None:
    """Run the Streamlit application shell."""
    st.set_page_config(
        page_title=settings.app_name,
        page_icon=":material/description:",
        layout="wide",
    )

    render_banner()
    render_upload_placeholder()
    st.info("Step 2 - Project Initialization Completed")


if __name__ == "__main__":
    main()
