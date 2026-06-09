"""Streamlit entry point for the Internal Document RAG Chatbot."""

from __future__ import annotations

import streamlit as st

from app.config import settings
from app.ui.streamlit_ui import render_upload_workspace


def render_banner() -> None:
    st.title("Internal Document RAG Chatbot")
    st.caption(
        "Secure internal document question answering powered by LangChain, "
        "ChromaDB, Sentence Transformers, and Gemini."
    )


def main() -> None:
    """Run the Streamlit application."""
    st.set_page_config(
        page_title=settings.app_name,
        page_icon=":material/description:",
        layout="wide",
    )

    render_banner()
    st.caption("Phase: Day 1 - PDF Upload & Extraction")
    render_upload_workspace()


if __name__ == "__main__":
    main()
