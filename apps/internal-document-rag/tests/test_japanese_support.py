"""Unit tests for Native Japanese Language Support."""

from pathlib import Path

from app.ingestion.chunker import DocumentChunker
from app.ingestion.text_loader import TextLoader
from app.llm.prompt_builder import PromptBuilder
from app.utils.language_detector import detect_language
from app.utils.localization import get_message


def test_language_detection() -> None:

    ja_query = "年間有給休暇は何日ありますか？"
    en_query = "How many annual leave days are provided?"

    assert detect_language(ja_query) == "ja"
    assert detect_language(en_query) == "en"
    assert detect_language("") == "en"
    assert detect_language("   ") == "en"


def test_localization_mappings() -> None:

    en_insufficient = get_message("insufficient_information", "en")
    assert "sufficient information" in en_insufficient

    # Japanese
    ja_insufficient = get_message("insufficient_information", "ja")
    assert "十分な情報がありません" in ja_insufficient

    # Fallback to English for unsupported language
    fr_insufficient = get_message("insufficient_information", "fr")
    assert fr_insufficient == en_insufficient


def test_prompt_builder_language_aware() -> None:
    context = "Employee handbook extract contents."
    question_en = "What are the rules?"
    question_ja = "ルールは何ですか？"

    # English query prompt
    prompt_en = PromptBuilder.build_rag_prompt(
        question_en, context, query_language="en"
    )
    assert "The uploaded documents do not contain sufficient information" in prompt_en
    assert "Answer the question using ONLY the information provided" in prompt_en
    assert "回答は日本語で作成してください" not in prompt_en

    # Japanese query prompt
    prompt_ja = PromptBuilder.build_rag_prompt(
        question_ja, context, query_language="ja"
    )
    assert (
        "アップロードされたドキュメントには、この質問に回答するための十分な情報がありません"
        in prompt_ja
    )
    assert "回答は日本語で作成してください" in prompt_ja
    assert "回答には、提供されたDocument contextの情報だけを使用してください" in prompt_ja


def test_japanese_file_load_encodings(tmp_path: Path) -> None:
    content_ja = "これは日本語のテストファイルコンテンツです。"
    loader = TextLoader()

    encodings_to_test = ["utf-8", "utf-8-sig", "shift_jis", "cp932"]
    for encoding in encodings_to_test:
        temp_file = tmp_path / f"test_{encoding}.txt"
        temp_file.write_text(content_ja, encoding=encoding)

        extracted_doc = loader.extract(temp_file)
        assert extracted_doc.source_file == temp_file.name
        assert extracted_doc.document_type == "txt"
        assert extracted_doc.pages[0].content == content_ja


def test_japanese_chunking() -> None:

    from app.models.schemas import ExtractedPage, ExtractedPdfDocument

    content = "従業員は有給休暇を取得できます。年間有給休暇は22日です。これらはすべて承認が必要です。"
    extracted_doc = ExtractedPdfDocument(
        source_file="handbook.txt",
        file_path=Path("handbook.txt"),
        document_type="txt",
        pages=[ExtractedPage(page_number=1, content=content)],
    )

    # Use a small chunk size to trigger separation at punctuation
    chunker = DocumentChunker(chunk_size=30, chunk_overlap=0)
    chunks = chunker.chunk_document(extracted_doc)

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.content) <= 30
        assert chunk.content.endswith("。") or "。" not in chunk.content


def test_japanese_sample_doc_qa_verification() -> None:

    ja_overview = Path("sample_docs/admin/japanese_overview_and_org.txt")
    if not ja_overview.exists():
        return

    text = ja_overview.read_text(encoding="utf-8")
    assert "リナス・スターリング博士" in text
    assert "ミッション" in text

    # Verify language detection for Japanese queries
    assert detect_language("エーテリスのミッションは何ですか？") == "ja"
    assert detect_language("最高技術責任者（CTO）は誰ですか？") == "ja"

    # Test prompt construction for Japanese queries
    prompt_mission = PromptBuilder.build_rag_prompt(
        "エーテリスのミッションは何ですか？", text, query_language="ja"
    )
    assert "回答は日本語で作成してください" in prompt_mission
    assert "回答には、提供されたDocument contextの情報だけを使用してください" in prompt_mission
