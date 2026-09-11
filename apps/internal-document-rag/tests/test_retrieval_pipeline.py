"""Unit tests for the end-to-end retrieval and QA generation pipeline."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from app.embeddings.embedding_service import EmbeddingService
from app.models.query_result import QueryResultKind
from app.models.schemas import ChunkMetadata, DocumentChunk
from app.retrieval.bm25_index_manager import BM25IndexManager
from app.services.query_service import QueryService
from app.vectorstore.chroma_manager import ChromaVectorStore


class MockLLMProvider:
    """Mock LLM provider to verify grounding context and responses."""

    def __init__(self, response_text: str = "Mock answer.") -> None:
        self.response_text = response_text
        self.last_prompt = ""

    def generate_response(
        self, prompt: str, system_instruction: str | None = None
    ) -> str:
        self.last_prompt = prompt
        return self.response_text


class FakeEmbeddingModel:
    """Mock model to return deterministic embedding vectors."""

    def __init__(self, embeddings: list[list[float]] | None = None) -> None:
        self.embeddings = embeddings or [[0.1, 0.2, 0.3]]

    def encode(self, texts: list[str], *args, **kwargs) -> list[list[float]]:
        return [self.embeddings[i % len(self.embeddings)] for i in range(len(texts))]


def _chunk(chunk_id: str, content: str) -> DocumentChunk:
    return DocumentChunk(
        content=content,
        metadata=ChunkMetadata(
            source_file="policy.pdf",
            page_number=1,
            chunk_id=chunk_id,
            document_type="pdf",
        ),
    )


def test_end_to_end_retrieval_pipeline(tmp_path: Path) -> None:
    username = "pipeline_user"

    # Mock LLM response
    fake_llm = MockLLMProvider("Grounding test response.")

    # Setup mock embedding service
    model = FakeEmbeddingModel(embeddings=[[0.9, 0.0, 0.0], [0.0, 0.9, 0.0]])
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

    with (
        override_settings(
            data_dir=tmp_path,
            upload_dir=tmp_path / "uploads",
            chroma_db_dir=tmp_path / "chroma",
            chroma_collection_name="test_pipeline_collection",
            allowed_upload_extensions=("pdf", "txt"),
            embedding_model_name="mock-model",
            embedding_dimension=3,
            embedding_batch_size=32,
            semantic_top_k=5,
            bm25_top_k=5,
            rrf_k=60,
            retrieval_top_k=3,
            retrieval_min_similarity=0.3,
            enable_hybrid_search=True,
        ),
        patch("app.services.query_service.get_llm_provider", return_value=fake_llm),
    ):

        store = ChromaVectorStore(
            persist_directory=tmp_path / "chroma",
            collection_name="test_pipeline_collection",
        )

        chunks = [
            _chunk(
                "c1",
                "Annual leave policy: 20 days off. Laptop model AE-0002 is Dell Precision. Paid leave in Japanese is 有給休暇.",
            ),
            _chunk("c2", "The product code is APEX-PATIENT-DB."),
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

        with (
            patch("app.retrieval.retriever.EmbeddingService", return_value=emb_service),
            patch("app.retrieval.retriever.ChromaVectorStore", return_value=store),
        ):

            # 1. English query flow
            res_en = QueryService.process_question(
                "What is the laptop model?", username, "en", bm25_index_manager=bm25
            )
            assert res_en.kind == QueryResultKind.SUCCESS
            assert "Grounding test response." in res_en.answer

            # 2. Japanese query flow (retrieves c1, prompts LLM for Japanese answer)
            res_ja = QueryService.process_question(
                "有給休暇は何日？", username, "ja", bm25_index_manager=bm25
            )
            assert res_ja.kind == QueryResultKind.SUCCESS

            # 3. Noisy query cleaning & matching
            res_noisy = QueryService.process_question(
                "####### What laptop model? &&&&&&&&",
                username,
                "en",
                bm25_index_manager=bm25,
            )
            assert res_noisy.kind == QueryResultKind.SUCCESS

            # 4. Typo handling (e.g. Lapotp instead of Laptop)
            res_typo = QueryService.process_question(
                "Lapotp model?", username, "en", bm25_index_manager=bm25
            )
            assert res_typo.kind == QueryResultKind.SUCCESS

            # 5. Mixed language query: "Dell Precisionとは何ですか？"
            res_mixed = QueryService.process_question(
                "Dell Precisionとは何ですか？", username, "ja", bm25_index_manager=bm25
            )
            assert res_mixed.kind == QueryResultKind.SUCCESS

            # 6. Employee ID / specific code lookup
            res_code = QueryService.process_question(
                "AE-0002", username, "en", bm25_index_manager=bm25
            )
            assert res_code.kind == QueryResultKind.SUCCESS

            # 7. Exact keyword vs semantic match
            res_exact = QueryService.process_question(
                "APEX-PATIENT-DB", username, "en", bm25_index_manager=bm25
            )
            assert res_exact.kind == QueryResultKind.SUCCESS
