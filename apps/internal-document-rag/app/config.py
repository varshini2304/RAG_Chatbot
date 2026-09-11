"""Centralized application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_ANONYMIZED_TELEMETRY"] = "False"
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="huggingface_hub")


def _path_from_env(env_name: str, default: Path) -> Path:
    """Return a normalized path from env or the provided default."""
    raw_value = os.getenv(env_name)
    if not raw_value:
        return default
    return Path(raw_value).expanduser().resolve()


@dataclass(frozen=True)
class Settings:

    app_name: str = "Internal Document RAG Chatbot"
    environment: str = os.getenv("APP_ENV", "development")
    llm_provider: str = os.getenv("LLM_PROVIDER", "groq")
    google_api_key: str | None = os.getenv("GOOGLE_API_KEY")
    groq_api_key: str | None = os.getenv("GROQ_API_KEY")
    embedding_model_name: str = os.getenv(
        "EMBEDDING_MODEL_NAME",
        "BAAI/bge-m3",
    )
    gemini_model_name: str = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
    groq_model_name: str = os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile")

    # Failover & fallback configurations
    primary_provider: str = os.getenv(
        "PRIMARY_PROVIDER", os.getenv("LLM_PROVIDER", "groq")
    )
    secondary_provider: str = os.getenv("SECONDARY_PROVIDER", "gemini")
    tertiary_provider: str = os.getenv("TERTIARY_PROVIDER", "ollama")
    ollama_model: str = os.getenv(
        "OLLAMA_MODEL_NAME", os.getenv("OLLAMA_MODEL", "gemma3:4b")
    )
    ollama_vision_model: str = os.getenv("OLLAMA_VISION_MODEL", "llava:latest")
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")

    # Request timeouts
    groq_timeout: float = float(os.getenv("GROQ_TIMEOUT", "30.0"))
    gemini_timeout: float = float(os.getenv("GEMINI_TIMEOUT", "30.0"))
    ollama_timeout: float = float(os.getenv("OLLAMA_TIMEOUT", "180.0"))

    # Circuit breaker settings
    circuit_breaker_threshold: int = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "2"))
    circuit_breaker_cooldown: int = int(os.getenv("CIRCUIT_BREAKER_COOLDOWN", "60"))

    data_dir: Path = _path_from_env("DATA_DIR", PROJECT_ROOT / "data")  # noqa: RUF009
    upload_dir: Path = _path_from_env(  # noqa: RUF009
        "UPLOAD_DIR", PROJECT_ROOT / "data" / "uploads"
    )
    chroma_db_dir: Path = _path_from_env(  # noqa: RUF009
        "CHROMA_DB_DIR", PROJECT_ROOT / "data" / "chroma_db"
    )
    chroma_collection_name: str = os.getenv(
        "CHROMA_COLLECTION_NAME",
        "internal_document_chunks_multilingual_v1",
    )
    sample_docs_dir: Path = _path_from_env(  # noqa: RUF009
        "SAMPLE_DOCS_DIR", PROJECT_ROOT / "sample_docs"
    )
    max_upload_size_mb: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
    allowed_upload_extensions: tuple[str, ...] = (
        "pdf",
        "txt",
        "png",
        "jpg",
        "jpeg",
        "webp",
        "tiff",
        "bmp",
    )

    image_extensions: tuple[str, ...] = ("png", "jpg", "jpeg", "webp", "tiff", "bmp")

    # Video Intake Configurations (Day 3)
    video_max_file_size_mb: int = int(os.getenv("VIDEO_MAX_FILE_SIZE_MB", "2048"))
    video_max_duration_sec: float = float(os.getenv("VIDEO_MAX_DURATION_SEC", "7200.0"))
    video_supported_codecs: tuple[str, ...] = tuple(
        c.strip().lower() for c in os.getenv("VIDEO_SUPPORTED_CODECS", "h264,vp9").split(",") if c.strip()
    )
    video_supported_formats: tuple[str, ...] = tuple(
        f.strip().lower()
        for f in os.getenv(
            "VIDEO_SUPPORTED_FORMATS",
            "mp4,mov,m4a,3gp,3g2,mj2,webm,matroska,matroska,webm,mov,mp4,m4a,3gp,3g2,mj2",
        ).split(",")
        if f.strip()
    )

    @property
    def video_max_size_bytes(self) -> int:
        """Returns the maximum video file size converted to bytes."""
        return self.video_max_file_size_mb * 1024 * 1024

    # Audio Extraction & Speech-to-Text (ASR) Configurations (Step 3)
    audio_sample_rate: int = int(os.getenv("AUDIO_SAMPLE_RATE", "16000"))
    audio_channels: int = int(os.getenv("AUDIO_CHANNELS", "1"))
    audio_sample_width_bytes: int = int(os.getenv("AUDIO_SAMPLE_WIDTH_BYTES", "2"))
    audio_enable_loudnorm: bool = os.getenv(
        "AUDIO_ENABLE_LOUDNORM", "true"
    ).lower() in ("true", "1", "yes")
    audio_loudnorm_target_i: float = float(os.getenv("AUDIO_LOUDNORM_TARGET_I", "-23.0"))
    audio_loudnorm_lra: float = float(os.getenv("AUDIO_LOUDNORM_LRA", "7.0"))
    audio_loudnorm_tp: float = float(os.getenv("AUDIO_LOUDNORM_TP", "-2.0"))
    audio_enable_silence_trimming: bool = os.getenv(
        "AUDIO_ENABLE_SILENCE_TRIMMING", "false"
    ).lower() in ("true", "1", "yes")
    audio_silence_threshold_db: float = float(os.getenv("AUDIO_SILENCE_THRESHOLD_DB", "-50.0"))
    audio_silence_duration_sec: float = float(os.getenv("AUDIO_SILENCE_DURATION_SEC", "0.2"))
    audio_duration_tolerance_sec: float = float(os.getenv("AUDIO_DURATION_TOLERANCE_SEC", "2.0"))

    whisper_model_size: str = os.getenv("WHISPER_MODEL_SIZE", "base")
    whisper_compute_type: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
    whisper_device: str = os.getenv("WHISPER_DEVICE", "cpu")
    whisper_beam_size: int = int(os.getenv("WHISPER_BEAM_SIZE", "5"))
    whisper_vad_filter: bool = os.getenv("WHISPER_VAD_FILTER", "true").lower() in (
        "true",
        "1",
        "yes",
    )
    whisper_word_timestamps: bool = os.getenv(
        "WHISPER_WORD_TIMESTAMPS", "true"
    ).lower() in ("true", "1", "yes")

    chunk_size: int = int(os.getenv("CHUNK_SIZE", "800"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "120"))
    embedding_batch_size: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))
    embedding_dimension: int = int(os.getenv("EMBEDDING_DIMENSION", "1024"))
    enable_contradiction_detection: bool = os.getenv(
        "ENABLE_CONTRADICTION_DETECTION", "True"
    ).lower() in ("true", "1", "yes")
    offline_mode: bool = os.getenv("OFFLINE_MODE", "False").lower() in (
        "true",
        "1",
        "yes",
    )
    embedding_offline_mode: bool = os.getenv(
        "EMBEDDING_OFFLINE_MODE", "True"
    ).lower() in (
        "true",
        "1",
        "yes",
    )
    hf_hub_offline: bool = os.getenv("HF_HUB_OFFLINE", "False").lower() in (
        "true",
        "1",
        "yes",
    )
    hf_hub_download_timeout: float = float(
        os.getenv(
            "HF_HUB_DOWNLOAD_TIMEOUT", os.getenv("EMBEDDING_DOWNLOAD_TIMEOUT", "15.0")
        )
    )
    retrieval_top_k: int = int(os.getenv("RETRIEVAL_TOP_K", "5"))
    retrieval_min_similarity: float = float(
        os.getenv("RETRIEVAL_MIN_SIMILARITY", "0.3")
    )
    enable_hybrid_search: bool = os.getenv("ENABLE_HYBRID_SEARCH", "True").lower() in (
        "true",
        "1",
        "yes",
    )
    semantic_top_k: int = int(os.getenv("SEMANTIC_TOP_K", "10"))
    bm25_top_k: int = int(os.getenv("BM25_TOP_K", "10"))
    rrf_k: int = int(os.getenv("RRF_K", "60"))
    # OCR Configurations
    ocr_language: str = os.getenv("OCR_LANGUAGE", "en")
    ocr_dpi: int = int(os.getenv("OCR_DPI", "200"))
    ocr_confidence_threshold: float = float(
        os.getenv("OCR_CONFIDENCE_THRESHOLD", "0.5")
    )
    ocr_scanned_page_threshold: int = int(
        os.getenv("OCR_SCANNED_PAGE_THRESHOLD", "300")
    )
    enable_ocr_preprocessing: bool = os.getenv(
        "ENABLE_OCR_PREPROCESSING", "True"
    ).lower() in ("true", "1", "yes")
    enable_ocr_cache: bool = os.getenv("ENABLE_OCR_CACHE", "True").lower() in (
        "true",
        "1",
        "yes",
    )

    chat_history_dir: Path = _path_from_env(  # noqa: RUF009
        "CHAT_HISTORY_DIR", PROJECT_ROOT / "data" / "chats"
    )
    user_credentials: str = os.getenv("USER_CREDENTIALS", "admin:admin123,user:user123")

    # PostgreSQL — required for User Portal persistent user registration.
    # When absent, AuthManager falls back to the legacy registered_users.json file.
    database_url: str | None = os.getenv("DATABASE_URL")

    # User Portal JWT Authentication
    user_jwt_secret: str = os.getenv(
        "USER_JWT_SECRET",
        "change-me-in-production-a3f9b2c1d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0",
    )
    user_jwt_algorithm: str = os.getenv("USER_JWT_ALGORITHM", "HS256")
    user_jwt_expire_minutes: int = int(os.getenv("USER_JWT_EXPIRE_MINUTES", "480"))


settings = Settings()
