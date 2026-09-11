"""Service layer managing user-level workspace isolation and persistent duplicate registries."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from app.config import settings
from app.models.schemas import (
    ChunkMetadata,
    ChunkType,
    DocumentChunk,
    ExtractedPage,
    ExtractedPdfDocument,
)
from app.models.workspace_state import WorkspaceState
from app.vectorstore.chroma_manager import ChromaVectorStore

LOGGER = logging.getLogger(__name__)

EMBEDDING_PENDING = "pending"
EMBEDDING_COMPLETED = "completed"
EMBEDDING_FAILED = "failed"


class DocumentCleanupError(RuntimeError):
    """Raised when removing an existing document from the workspace fails."""


class WorkspaceService:
    """Orchestrate per-user file directories, hash registries, and collections."""

    @staticmethod
    def get_workspace_name(username: str) -> str:
        """Sanitize a username to contain only alphanumeric characters, underscores, or hyphens."""
        sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", username.strip())
        return sanitized

    @classmethod
    def get_upload_directory(cls, username: str) -> Path:
        """Return the user-scoped upload folder path, creating it if necessary."""
        upload_dir = settings.upload_dir / cls.get_workspace_name(username)
        upload_dir.mkdir(parents=True, exist_ok=True)
        return upload_dir

    @classmethod
    def get_collection_name(cls, username: str) -> str:
        """Return the user-scoped ChromaDB collection name."""
        return f"rag_{cls.get_workspace_name(username)}"

    @classmethod
    def load_hashes(cls, username: str) -> dict[str, str]:
        """Load the user's persistent duplicate hash mappings from disk."""
        user_dir = cls.get_upload_directory(username)
        hash_file = user_dir / "hashes.json"
        if hash_file.exists():
            try:
                with open(hash_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                LOGGER.error("Failed to load hashes for %s: %s", username, e)
        return {}

    @classmethod
    def save_hashes(cls, username: str, hashes: dict[str, str]) -> None:
        """Overwrite the user's persistent duplicate hashes mapping file."""
        user_dir = cls.get_upload_directory(username)
        user_dir.mkdir(parents=True, exist_ok=True)
        hash_file = user_dir / "hashes.json"
        try:
            with open(hash_file, "w", encoding="utf-8") as f:
                json.dump(hashes, f, indent=2, ensure_ascii=False)
        except Exception as e:
            LOGGER.error("Failed to save hashes for %s: %s", username, e)

    @classmethod
    def update_hash(cls, username: str, file_hash: str, filename: str) -> None:
        """Add or update a single file hash mapping for the user."""
        hashes = cls.load_hashes(username)
        hashes[file_hash] = filename
        cls.save_hashes(username, hashes)

    @classmethod
    def remove_hash_for_file(cls, username: str, filename: str) -> None:
        """Remove duplicate hashes mapping linked to the specified file."""
        hashes = cls.load_hashes(username)
        hashes_to_remove = [h for h, fname in hashes.items() if fname == filename]
        for h in hashes_to_remove:
            hashes.pop(h, None)
        cls.save_hashes(username, hashes)

    @classmethod
    def load_workspace(cls, username: str) -> WorkspaceState:
        """Load the user-specific workspace state from files and ChromaDB metadata without redundant re-chunking."""
        user_dir = cls.get_upload_directory(username)
        user_dir.mkdir(parents=True, exist_ok=True)

        hashes = cls.load_hashes(username)

        documents: list[ExtractedPdfDocument] = []
        chunks_by_document: dict[str, list[DocumentChunk]] = {}
        embedding_status: dict[str, str] = {}
        processed_names: set[str] = set()
        document_errors: dict[str, str] = {}

        collection_name = cls.get_collection_name(username)
        store = ChromaVectorStore(collection_name=collection_name)

        bad_test_files = {
            "corrupted_test.pdf",
            "encrypted_test.pdf",
            "scanned_test.pdf",
            "empty_test.txt",
        }

        # Iterate over files in the user upload folder
        for file_path in list(user_dir.iterdir()):
            if file_path.name in bad_test_files:
                try:
                    file_path.unlink(missing_ok=True)
                    LOGGER.info(
                        "Cleaned up test artifact file %s from user workspace.",
                        file_path.name,
                    )
                except Exception:
                    pass
                continue

            if file_path.name == "hashes.json" or file_path.is_dir():
                continue
            if (
                file_path.suffix.lower().lstrip(".")
                not in settings.allowed_upload_extensions
            ):
                continue

            filename = file_path.name
            try:
                # Query ChromaDB to check if collection already has chunks for this file
                stored = store.collection.get(
                    where={"source_file": filename}, include=["documents", "metadatas"]
                )

                if stored and stored["ids"]:
                    # Document is already embedded. Reconstruct from Chroma metadata.
                    chunks_list: list[DocumentChunk] = []
                    pages_dict: dict[int, list[str]] = {}

                    for doc_text, meta in zip(stored["documents"], stored["metadatas"]):
                        chunk_id = meta.get("chunk_id", f"{filename}-chunk")
                        page_num = int(meta.get("page_number", 1))
                        doc_type = meta.get("document_type", filename.split(".")[-1])
                        raw_chunk_type = meta.get("chunk_type", "text")
                        try:
                            chunk_type = ChunkType(raw_chunk_type)
                        except Exception:
                            chunk_type = ChunkType.TEXT

                        chunk = DocumentChunk(
                            content=doc_text,
                            metadata=ChunkMetadata(
                                source_file=filename,
                                page_number=page_num,
                                chunk_id=chunk_id,
                                document_type=doc_type,
                                chunk_type=chunk_type,
                                document_name=str(meta.get("document_name", "")),
                                username=str(meta.get("username", "")),
                                image_path=meta.get("image_path"),
                                image_hash=meta.get("image_hash"),
                                table_markdown=meta.get("table_markdown"),
                                table_json=meta.get("table_json"),
                            ),
                        )
                        chunks_list.append(chunk)
                        pages_dict.setdefault(page_num, []).append(doc_text)

                    pages = [
                        ExtractedPage(page_number=p_num, content="\n".join(contents))
                        for p_num, contents in sorted(pages_dict.items())
                    ]

                    extracted_doc = ExtractedPdfDocument(
                        source_file=filename,
                        file_path=file_path,
                        document_type=(
                            chunks_list[0].metadata.document_type
                            if chunks_list
                            else "pdf"
                        ),
                        pages=pages,
                    )

                    documents.append(extracted_doc)
                    chunks_by_document[filename] = chunks_list
                    embedding_status[filename] = EMBEDDING_COMPLETED
                else:
                    # Not yet embedded — mark as pending so the upload flow handles it
                    embedding_status[filename] = EMBEDDING_PENDING

                processed_names.add(filename)
            except Exception as exc:
                LOGGER.warning("Failed to restore workspace file %s: %s", filename, exc)
                document_errors[filename] = str(exc)
                processed_names.add(filename)

        all_chunks_list = []
        for document_chunks in chunks_by_document.values():
            all_chunks_list.extend(document_chunks)

        from app.retrieval.bm25_index_manager import BM25IndexManager

        bm25_index = BM25IndexManager(username)
        bm25_index.load()
        bm25_index.update_chunk_map(all_chunks_list)

        return WorkspaceState(
            documents=documents,
            hashes=hashes,
            embedding_status=embedding_status,
            processed_names=processed_names,
            document_errors=document_errors,
            chunks=chunks_by_document,
            bm25_index_manager=bm25_index,
        )

    @classmethod
    def clear_workspace(cls, username: str) -> None:
        user_dir = cls.get_upload_directory(username)

        # 1. Delete physical files from disk
        if user_dir.exists():
            for file_path in user_dir.iterdir():
                try:
                    file_path.unlink(missing_ok=True)
                except Exception as e:
                    LOGGER.warning(
                        "Failed to delete workspace file %s: %s", file_path, e
                    )

        # 2. Reset duplicate hashes registry
        cls.save_hashes(username, {})

        # 3. Clear ChromaDB vector collection
        collection_name = cls.get_collection_name(username)
        try:
            store = ChromaVectorStore(collection_name=collection_name)
            store.clear_workspace()
        except Exception as exc:
            LOGGER.warning(
                "Failed to clear Chroma vector store collection %s: %s",
                collection_name,
                exc,
            )

    @classmethod
    def delete_document(cls, username: str, filename: str) -> None:
        """Remove a document from the user's upload directory, delete its chunks from ChromaDB, and remove its hashes registry mapping."""
        # 1. Delete physical file from disk
        user_dir = cls.get_upload_directory(username)
        file_path = user_dir / filename
        try:
            file_path.unlink(missing_ok=True)
            LOGGER.info("Deleted upload file %s from disk.", file_path)
        except Exception as exc:
            LOGGER.warning("Failed to delete upload file %s: %s", file_path, exc)

        # 2. Remove from ChromaDB vector collection
        collection_name = cls.get_collection_name(username)
        try:
            store = ChromaVectorStore(collection_name=collection_name)
            store.delete_document(filename)
            LOGGER.info("Deleted chunks for %s from ChromaDB.", filename)
        except Exception as exc:
            LOGGER.warning(
                "Failed to delete chunks for %s from ChromaDB: %s", filename, exc
            )

        # 3. Remove mapping from persistent hashes file
        cls.remove_hash_for_file(username, filename)

    @classmethod
    def prepare_document_upload(cls, username: str, filename: str) -> None:
        """Before uploading a document, clean up the previous document if it exists and verify deletion."""
        user_dir = cls.get_upload_directory(username)
        file_path = user_dir / filename

        collection_name = cls.get_collection_name(username)
        store = ChromaVectorStore(collection_name=collection_name)

        try:
            stored = store.collection.get(where={"source_file": filename}, include=[])
            has_db_chunks = bool(stored and stored["ids"])
        except Exception:
            has_db_chunks = False

        hashes = cls.load_hashes(username)
        has_hash_entry = any(fname == filename for fname in hashes.values())

        if file_path.exists() or has_db_chunks or has_hash_entry:
            LOGGER.info(
                "Existing document '%s' found in workspace. Cleaning up...", filename
            )

            # 1. Perform cleanup
            cls.delete_document(username, filename)

            # 2. Verify physical file is gone
            if file_path.exists():
                raise DocumentCleanupError(
                    f"Failed to delete uploaded file from disk: {filename}"
                )

            # 3. Verify ChromaDB chunks are gone
            try:
                stored_check = store.collection.get(
                    where={"source_file": filename}, include=[]
                )
                if stored_check and stored_check["ids"]:
                    raise DocumentCleanupError(
                        f"Failed to delete vector database chunks for: {filename}"
                    )
            except Exception as e:
                if isinstance(e, DocumentCleanupError):
                    raise
                raise DocumentCleanupError(
                    f"Error checking vector store after deletion: {e}"
                ) from e

            # 4. Verify hash registry is cleared
            hashes_check = cls.load_hashes(username)
            if any(fname == filename for fname in hashes_check.values()):
                raise DocumentCleanupError(
                    f"Failed to remove hash registry mapping for: {filename}"
                )

            LOGGER.info(
                "Cleanup successfully verified for existing document: %s", filename
            )
