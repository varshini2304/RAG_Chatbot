"""Embedding generation engine for document chunks."""

from __future__ import annotations

import logging
import math
import os
from collections.abc import Sequence
from typing import Any, ClassVar

from app.config import settings
from app.models.schemas import DocumentChunk

LOGGER = logging.getLogger(__name__)


def _normalize_vector(values: Sequence[float]) -> list[float]:
    """L2-normalize one embedding vector for cosine-compatible storage."""
    norm = math.sqrt(sum(float(value) * float(value) for value in values))
    if norm <= 0:
        raise EmbeddingEngineError("Embedding vectors must have non-zero magnitude.")
    return [float(value) / norm for value in values]


class EmbeddingEngineError(RuntimeError):
    """Raised when embedding model loading, generation, or validation fails."""


# Backwards-compatibility alias for the exception
EmbeddingServiceError = EmbeddingEngineError


class EmbeddingEngine:
    """Generate validated embeddings for document chunks using a cached model."""

    _model_cache: ClassVar[dict[str, Any]] = {}

    def __init__(
        self,
        model_name: str | None = None,
        batch_size: int = 32,
        expected_dimension: int | None = None,
        model: Any | None = None,
    ) -> None:
        if batch_size <= 0:
            raise EmbeddingEngineError(
                "Embedding batch_size must be greater than zero."
            )

        self.model_name = model_name or settings.embedding_model_name
        self.batch_size = batch_size
        self.expected_dimension = (
            expected_dimension
            if expected_dimension is not None
            else settings.embedding_dimension
        )
        if self.expected_dimension <= 0:
            raise EmbeddingEngineError(
                "Expected embedding dimension must be greater than zero."
            )
        # Store the model directly (either provided or will be loaded on first use)
        self._model = model
        self._model_name = model_name

    @classmethod
    def _load_model(cls, model_name: str) -> Any:
        if model_name in cls._model_cache:
            return cls._model_cache[model_name]

        LOGGER.info("Loading embedding model: %s", model_name)

        # Set network download timeout and disable unauthenticated HF token warning
        timeout_val = settings.hf_hub_download_timeout
        os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = str(int(timeout_val))
        os.environ["HTTP_TIMEOUT"] = str(int(timeout_val))
        os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN_WARNING"] = "1"
        os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
        logging.getLogger("huggingface_hub.utils._warnings").setLevel(logging.ERROR)

        # Import here to allow test patching in index_maintenance_service module
        try:
            from app.services.index_maintenance_service import SentenceTransformer
        except ImportError as exc:
            LOGGER.exception(
                "Embedding model loading failed for %s: %s", model_name, exc
            )
            raise EmbeddingEngineError(
                "Failed to import sentence-transformers."
            ) from exc

        model: Any = None
        offline_preferred = (
            settings.embedding_offline_mode
            or settings.hf_hub_offline
            or os.getenv("HF_HUB_OFFLINE") in ("1", "true", "True")
        )

        # 1. Attempt local offline load if offline mode preferred or model might be cached
        if offline_preferred:
            try:
                LOGGER.info(
                    "Attempting local offline load for embedding model '%s'...",
                    model_name,
                )
                os.environ["HF_HUB_OFFLINE"] = "1"
                os.environ["TRANSFORMERS_OFFLINE"] = "1"
                try:
                    model = SentenceTransformer(model_name, local_files_only=True)
                except TypeError:
                    model = SentenceTransformer(model_name)
                LOGGER.info(
                    "Successfully loaded embedding model '%s' from local cache in offline mode.",
                    model_name,
                )
            except Exception as local_exc:
                LOGGER.info(
                    "Local offline load for model '%s' did not find cached weights (%s). Checking online connection...",
                    model_name,
                    local_exc,
                )

        # 2. If model not loaded locally, attempt online download (unless HF_HUB_OFFLINE=1 is explicitly set in env)
        if model is None:
            if (
                os.getenv("HF_HUB_OFFLINE") == "1"
                and not settings.embedding_offline_mode
            ):
                err_msg = (
                    f"Failed to load embedding model '{model_name}' from local cache while HF_HUB_OFFLINE=1. "
                    f"If this is a first run, set HF_HUB_OFFLINE=0 in .env to allow downloading model weights."
                )
                LOGGER.error(err_msg)
                raise EmbeddingEngineError(err_msg)

            # Re-enable network for download with explicit timeout
            os.environ.pop("HF_HUB_OFFLINE", None)
            os.environ.pop("TRANSFORMERS_OFFLINE", None)

            LOGGER.info(
                "Connecting to Hugging Face Hub to load model '%s' (timeout=%ss)...",
                model_name,
                int(timeout_val),
            )

            try:
                try:
                    model = SentenceTransformer(model_name, local_files_only=False)
                except TypeError:
                    model = SentenceTransformer(model_name)
                LOGGER.info(
                    "Successfully fetched and loaded embedding model '%s' from Hugging Face Hub.",
                    model_name,
                )
            except Exception as exc:
                err_msg = (
                    f"Failed to reach Hugging Face Hub within {int(timeout_val)}s. "
                    f"If the embedding model is already cached, set HF_HUB_OFFLINE=1 in .env to skip this network check."
                )
                LOGGER.error(
                    "Failed to reach Hugging Face Hub within %ss for model '%s'. Error: %s",
                    int(timeout_val),
                    model_name,
                    exc,
                )
                raise EmbeddingEngineError(err_msg) from exc

        # 3. Once loaded successfully, enable offline mode in environment for future processes/calls
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"

        cls._model_cache[model_name] = model
        LOGGER.info("Embedding model ready and cached: %s", model_name)
        return cls._model_cache[model_name]

    @property
    def model(self) -> Any:
        """Get the embedding model, loading it lazily on first access."""
        if self._model is None:
            self._model = self._load_model(self.model_name)
        return self._model

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """Generate normalized embedding vectors for an arbitrary sequence of strings.

        Args:
            texts: Non-empty sequence of strings to encode.

        Returns:
            List of L2-normalized float embedding vectors.

        Raises:
            EmbeddingEngineError: If texts is empty, model fails, or embeddings cannot be generated.
        """
        if not texts:
            raise EmbeddingEngineError("Cannot embed an empty text list.")

        total_texts = len(texts)
        total_batches = math.ceil(total_texts / self.batch_size)
        raw: list[Any] = []
        try:
            for batch_idx in range(total_batches):
                start_i = batch_idx * self.batch_size
                end_i = min(start_i + self.batch_size, total_texts)
                batch_slice = list(texts[start_i:end_i])
                LOGGER.info(
                    "Embedding text batch %s/%s (items %s-%s)...",
                    batch_idx + 1,
                    total_batches,
                    start_i + 1,
                    end_i,
                )
                batch_vectors = self.model.encode(
                    batch_slice,
                    batch_size=self.batch_size,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                )
                if hasattr(batch_vectors, "tolist"):
                    batch_vectors = batch_vectors.tolist()
                raw.extend(batch_vectors)
                LOGGER.info(
                    "Completed text embedding batch %s/%s (%s items processed).",
                    batch_idx + 1,
                    total_batches,
                    end_i - start_i,
                )
        except Exception as exc:
            LOGGER.exception("Text embedding failed for %s texts", len(texts))
            raise EmbeddingEngineError("Failed to embed texts.") from exc

        return self._normalize_embeddings(raw)

    def generate_embeddings(self, chunks: Sequence[DocumentChunk]) -> list[list[float]]:
        """Generate one embedding vector for each supplied document chunk."""
        if not chunks:
            raise EmbeddingEngineError(
                "Cannot generate embeddings for an empty chunk list."
            )

        texts = [chunk.content for chunk in chunks]
        total_chunks = len(texts)
        total_batches = math.ceil(total_chunks / self.batch_size)
        LOGGER.info(
            "Generating embeddings for %s chunks across %s batch(es) (batch_size=%s)...",
            total_chunks,
            total_batches,
            self.batch_size,
        )

        raw_embeddings: list[Any] = []
        try:
            for batch_idx in range(total_batches):
                start_i = batch_idx * self.batch_size
                end_i = min(start_i + self.batch_size, total_chunks)
                batch_texts = texts[start_i:end_i]
                LOGGER.info(
                    "Embedding batch %s/%s (chunks %s-%s)...",
                    batch_idx + 1,
                    total_batches,
                    start_i + 1,
                    end_i,
                )
                batch_vectors = self.model.encode(
                    batch_texts,
                    batch_size=self.batch_size,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                )
                if hasattr(batch_vectors, "tolist"):
                    batch_vectors = batch_vectors.tolist()
                raw_embeddings.extend(batch_vectors)
                LOGGER.info(
                    "Completed embedding batch %s/%s (%s chunks processed).",
                    batch_idx + 1,
                    total_batches,
                    end_i - start_i,
                )
        except Exception as exc:
            LOGGER.exception("Embedding generation failed for %s chunks", len(texts))
            raise EmbeddingEngineError("Failed to generate embeddings.") from exc

        embeddings = self._normalize_embeddings(raw_embeddings)
        self.validate_embeddings(chunks, embeddings)
        LOGGER.info(
            "Generated %s embeddings with dimension=%s",
            len(embeddings),
            self.expected_dimension,
        )
        return embeddings

    def validate_embeddings(
        self,
        chunks: Sequence[DocumentChunk],
        embeddings: Sequence[Sequence[float]],
    ) -> None:
        """Validate embedding count and vector dimensional consistency."""
        if len(embeddings) != len(chunks):
            LOGGER.error(
                "Embedding validation failed: embedding_count=%s chunk_count=%s",
                len(embeddings),
                len(chunks),
            )
            raise EmbeddingEngineError("Embedding count must match chunk count.")

        if not embeddings:
            raise EmbeddingEngineError(
                "Embedding validation failed: no embeddings generated."
            )

        expected_dimension = len(embeddings[0])
        if expected_dimension != self.expected_dimension:
            LOGGER.error(
                "Embedding validation failed: dimension=%s expected=%s model=%s",
                expected_dimension,
                self.expected_dimension,
                self.model_name,
            )
            raise EmbeddingEngineError(
                f"Embedding dimension must be {self.expected_dimension}."
            )

        for index, embedding in enumerate(embeddings):
            if len(embedding) != expected_dimension:
                LOGGER.error(
                    "Embedding validation failed: vector at index=%s has dimension=%s expected=%s",
                    index,
                    len(embedding),
                    expected_dimension,
                )
                raise EmbeddingEngineError(
                    "All embedding vectors must have the same dimension."
                )
            if any(not math.isfinite(value) for value in embedding):
                LOGGER.error(
                    "Embedding validation failed: vector at index=%s contains non-finite values",
                    index,
                )
                raise EmbeddingEngineError(
                    "Embedding vectors must contain only finite values."
                )

    @staticmethod
    def _normalize_embeddings(raw_embeddings: Any) -> list[list[float]]:
        """Convert numpy arrays or nested sequences into Chroma-compatible lists."""
        if hasattr(raw_embeddings, "tolist"):
            raw_embeddings = raw_embeddings.tolist()

        try:
            return [_normalize_vector(embedding) for embedding in raw_embeddings]
        except (TypeError, ValueError, OverflowError) as exc:
            LOGGER.exception("Embedding normalization failed.")
            raise EmbeddingEngineError(
                "Embedding output could not be normalized."
            ) from exc


EmbeddingService = EmbeddingEngine
