
from __future__ import annotations

import json
from pathlib import Path

from app.models.schemas import ChunkMetadata, DocumentChunk
from app.retrieval.bm25_index_manager import BM25IndexManager


def _chunk(chunk_id: str, content: str, source_file: str = "doc.pdf") -> DocumentChunk:
    return DocumentChunk(
        content=content,
        metadata=ChunkMetadata(
            source_file=source_file,
            page_number=1,
            chunk_id=chunk_id,
            document_type="pdf",
        ),
    )


def test_bm25_index_lifecycle_and_json_persistence(tmp_path: Path) -> None:
    username = "test_user"
    storage_dir = tmp_path / "bm25_index"

    manager = BM25IndexManager(username=username, storage_dir=storage_dir)
    manager.load()

    # 1. Build index from 5 chunks
    chunks = [
        _chunk("c1", "First chunk for testing search capabilities.", "f1.pdf"),
        _chunk("c2", "Second document chunk about software architecture.", "f2.pdf"),
        _chunk("c3", "Third chunk containing employee policy information.", "f3.pdf"),
        _chunk("c4", "Fourth chunk about product engineering guides.", "f4.pdf"),
        _chunk("c5", "Fifth chunk discussing health and safety rules.", "f5.pdf"),
    ]
    manager.add_documents(chunks)

    # Assert BM25 index is initialized and 5 chunks are mapped
    assert manager._bm25 is not None
    assert len(manager._chunk_ids) == 5
    assert len(manager._tokenized_corpus) == 5

    # 2. Save corpus verification (JSON only, no pickle)
    corpus_file = storage_dir / "corpus.json"
    pickle_file = storage_dir / "index.pkl"

    assert corpus_file.exists()
    assert not pickle_file.exists()

    # Assert JSON contents are clean lists of string tokens
    with open(corpus_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "tokenized_corpus" in data
    assert "chunk_ids" in data
    assert len(data["chunk_ids"]) == 5
    assert all(isinstance(tokens, list) for tokens in data["tokenized_corpus"])

    # 3. Load corpus validation
    fresh_manager = BM25IndexManager(username=username, storage_dir=storage_dir)
    fresh_manager.load()

    assert len(fresh_manager._chunk_ids) == 5
    assert fresh_manager._bm25 is not None
    results = fresh_manager.search("software architecture", top_k=2)
    assert results
    assert results[0].metadata.source_file == "f2.pdf"


def test_bm25_incremental_mutations(tmp_path: Path) -> None:
    username = "test_user_mutate"
    storage_dir = tmp_path / "bm25_index_mutate"
    manager = BM25IndexManager(username=username, storage_dir=storage_dir)
    manager.load()

    # Add initial document
    manager.add_documents([_chunk("c1", "Initial document content.", "doc1.pdf")])
    assert len(manager._chunk_ids) == 1

    # Add another document (+1)
    manager.add_documents([_chunk("c2", "Second document content.", "doc2.pdf")])
    assert len(manager._chunk_ids) == 2

    # Delete document (-1)
    manager.remove_document_by_source("doc1.pdf")
    assert len(manager._chunk_ids) == 1
    assert manager._chunk_ids == ["c2"]

    # Clear workspace
    manager.clear()
    assert len(manager._chunk_ids) == 0
    assert not (storage_dir / "corpus.json").exists()


def test_bm25_japanese_tokenization() -> None:
    # Verify Japanese term tokenization generates character unigrams + bigrams
    tokens = BM25IndexManager._tokenize("教育費")

    # "教育費" unigrams: "教", "育", "費"
    # "教育費" bigrams: "教育", "育費"
    assert "教" in tokens
    assert "育" in tokens
    assert "費" in tokens
    assert "教育" in tokens
    assert "育費" in tokens

    # Verify punctuation / whitespace are not tokenized
    cleaned_tokens = BM25IndexManager._tokenize("教育費！ ？")
    assert "！" not in cleaned_tokens
    assert "？" not in cleaned_tokens
    assert " " not in cleaned_tokens
