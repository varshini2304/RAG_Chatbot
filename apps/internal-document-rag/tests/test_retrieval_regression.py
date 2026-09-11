"""Regression tests verifying previously reported noisy, multilingual, and keyword issues."""

from __future__ import annotations

from pathlib import Path

from app.embeddings.embedding_service import EmbeddingService
from app.models.schemas import ChunkMetadata, DocumentChunk
from app.retrieval.bm25_index_manager import BM25IndexManager
from app.retrieval.retrieval_service import RetrievalService
from app.vectorstore.chroma_manager import ChromaVectorStore


class FakeEmbeddingModel:
    """Mock model to return deterministic embedding vectors."""

    def __init__(self, embeddings: list[list[float]] | None = None) -> None:
        self.embeddings = embeddings or [[0.1, 0.2, 0.3]]
        self._mapping: dict[str, list[float]] = {}

    def encode(self, texts: list[str], *args, **kwargs) -> list[list[float]]:
        # Cycle or repeat vectors to assign deterministic embeddings to documents during ingestion
        generated = [
            self.embeddings[i % len(self.embeddings)] for i in range(len(texts))
        ]

        if len(texts) > 1:
            for text, emb in zip(texts, generated):
                self._mapping[text] = emb

        res = []
        for text in texts:
            if text in self._mapping:
                res.append(self._mapping[text])
            else:
                # Find the key with the highest token/character overlap
                best_key = None
                best_score = -1.0

                import re

                words_text = {w.lower() for w in re.split(r"\W+", text) if w}
                chars_text = {c.lower() for c in text if c.isalnum()}

                for key in self._mapping:
                    words_key = {w.lower() for w in re.split(r"\W+", key) if w}
                    chars_key = {c.lower() for c in key if c.isalnum()}

                    word_overlap = len(words_text & words_key)
                    char_overlap = len(chars_text & chars_key)
                    score = word_overlap * 10.0 + char_overlap

                    if score > best_score:
                        best_score = score
                        best_key = key

                if best_key is not None and best_score > 0:
                    res.append(self._mapping[best_key])
                else:
                    idx = texts.index(text)
                    res.append(generated[idx])
        return res


def _chunk(chunk_id: str, content: str) -> DocumentChunk:
    return DocumentChunk(
        content=content,
        metadata=ChunkMetadata(
            source_file="regression_policy.pdf",
            page_number=1,
            chunk_id=chunk_id,
            document_type="pdf",
        ),
    )


def test_retrieval_quality_regressions(tmp_path: Path) -> None:
    username = "regression_user"

    model = FakeEmbeddingModel(
        embeddings=[
            [0.8, 0.1, 0.1],  # c1 (Dell Precision laptop)
            [0.1, 0.8, 0.1],  # c2 (Annual limit)
            [0.1, 0.1, 0.8],  # c3 (Employee ID AE-0002)
        ]
    )
    emb_service = EmbeddingService(model=model, expected_dimension=3)

    from contextlib import contextmanager

    from app.config import settings as app_settings

    @contextmanager
    def override_settings(**kwargs):
        originals = {k: getattr(app_settings, k) for k in kwargs}
        try:
            for k, v in kwargs.items():
                object.__setattr__(app_settings, k, v)
            yield
        finally:
            for k, v in originals.items():
                object.__setattr__(app_settings, k, v)

    with override_settings(
        data_dir=tmp_path,
        upload_dir=tmp_path / "uploads",
        chroma_db_dir=tmp_path / "chroma",
        chroma_collection_name="test_regression_collection",
        embedding_model_name="mock-model",
        embedding_dimension=3,
        embedding_batch_size=32,
        semantic_top_k=5,
        bm25_top_k=5,
        rrf_k=60,
        retrieval_top_k=3,
        retrieval_min_similarity=0.3,
        enable_hybrid_search=True,
    ):

        store = ChromaVectorStore(
            persist_directory=tmp_path / "chroma",
            collection_name="test_regression_collection",
        )

        chunks = [
            _chunk(
                "c1",
                "エンジニアリング部門のスタッフには、Dell Precision Workstationモデルのノートパソコンが支給されています。",
            ),
            _chunk("c2", "The annual paid leave reimbursement limit is $5000."),
            _chunk("c3", "The employee profile record contains Employee ID: AE-0002."),
        ]

        # Generate vectors and add
        vectors = emb_service.embed_texts([c.content for c in chunks])
        store.collection.add(
            ids=[c.metadata.chunk_id for c in chunks],
            embeddings=vectors,
            metadatas=[c.metadata.to_chroma_dict() for c in chunks],
            documents=[c.content for c in chunks],
        )

        bm25 = BM25IndexManager(username=username, storage_dir=tmp_path / "bm25")
        bm25.add_documents(chunks)

        retrieval = RetrievalService(
            embedding_service=emb_service,
            vector_store=store,
            top_k=3,
            enable_hybrid_search=True,
            bm25_index_manager=bm25,
        )

        # Test 1: Multilingual Japanese query retrieves correct Dell Precision chunk
        res_t1 = retrieval.search(
            "エンジニアリング部門のスタッフには、どのようなブランドやモデルのノートパソコンが支給されていますか？",
            top_k=1,
        )
        assert len(res_t1) == 1
        assert res_t1[0].metadata.chunk_id == "c1"

        # Test 2: Paraphrased Japanese query retrieves the exact same chunk (c1)
        res_t2 = retrieval.search(
            "エンジニアスタッフにはどのノートパソコンのブランドやモデルが提供されていますか？",
            top_k=1,
        )
        assert len(res_t2) == 1
        assert res_t2[0].metadata.chunk_id == "c1"

        # Test 3: Noisy query cleans and retrieves correct leave limits
        res_t3 = retrieval.search(
            "################# What is the annual &&&&&&&& limit?", top_k=1
        )
        assert len(res_t3) == 1
        assert res_t3[0].metadata.chunk_id == "c2"

        # Test 4: Keyword search matches employee ID AE-0002
        res_t4 = retrieval.search("AE-0002", top_k=1)
        assert len(res_t4) == 1
        assert res_t4[0].metadata.chunk_id == "c3"
