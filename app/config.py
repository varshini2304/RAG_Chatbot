

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:

    app_name: str = "Internal Document RAG Chatbot"
    environment: str = os.getenv("APP_ENV", "development")
    google_api_key: str | None = os.getenv("GOOGLE_API_KEY")
    embedding_model_name: str = "multi-qa-MiniLM-L6-cos-v1"
    gemini_model_name: str = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
    upload_dir: Path = PROJECT_ROOT / "data" / "uploads"
    chroma_db_dir: Path = PROJECT_ROOT / "data" / "chroma_db"
    sample_docs_dir: Path = PROJECT_ROOT / "sample_docs"
    max_upload_size_mb: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
    allowed_upload_extensions: tuple[str, ...] = ("pdf",)


settings = Settings()
