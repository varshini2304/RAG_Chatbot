class PromptBuilder:
    """Build consistent grounded prompts for all LLM providers."""

    @staticmethod
    def build_rag_prompt(
        question: str, context: str, query_language: str = "en"
    ) -> str:
        """
        Construct a strict grounded RAG prompt designed to minimize hallucination
        and ensure clean Markdown formatting for multi-item answers.
        """

        if query_language == "ja":
            return (
                "あなたは社内文書を検索して回答するアシスタントです。\n\n"

                "重要なルール:\n"
                "1. 回答には、提供されたDocument contextの情報だけを使用してください。\n"
                "2. 質問が簡潔または広範であっても、Document contextに関連情報が含まれている場合は、その情報を使って明確に回答してください。\n"
                "3. 複数のコンテキストの関連情報を必要に応じてまとめて回答してください。\n"
                "4. 質問に必要な情報がDocument contextに全く含まれていない場合のみ、次の文章をそのまま回答してください:\n"
                "「アップロードされたドキュメントには、この質問に回答するための十分な情報がありません。」\n"
                "5. 一般知識、推測、外部情報を使用しないでください。\n"
                "6. 回答は簡潔で、Document contextに直接根拠がある内容にしてください。\n"
                "7. 回答は日本語で作成してください。\n"
                "8. フォーマット: 複数の項目、サービス、製品、特徴が含まれる場合は、見出し（###）や箇条書き（- **項目名:** 説明）を使って読みやすく整理してください。単一のシンプルな質問には箇条書きを無理に使わず直接回答してください。\n\n"

                f"Document context:\n{context}\n\n"
                f"Question:\n{question}\n\n"
                "Answer:"
            )

        return (
            "You are a grounded document question-answering assistant.\n\n"

            "STRICT RULES:\n"
            "1. Answer the question using ONLY the information provided in the Document context.\n"
            "2. If the Document context contains relevant information (even if the question is short or broad), synthesize a clear answer using that text.\n"
            "3. Combine relevant details from multiple context blocks when helpful.\n"
            "4. Do NOT refuse to answer merely because the question is concise or broad.\n"
            "5. ONLY if the topic/information is completely absent from the Document context, respond exactly with:\n"
            "\"The uploaded documents do not contain sufficient information to answer this question.\"\n"
            "6. Do NOT use outside knowledge, assumptions, or invented facts.\n"
            "7. Keep the answer strictly supported by the Document context.\n"
            "8. FORMATTING: When the answer contains multiple distinct items, services, products, or features, organize them using clean Markdown headings (###) and bullet lists with bold labels (- **Category:** Description). Prefer readable structured Markdown over long dense paragraphs. For simple questions, provide a direct answer without forcing unnecessary lists.\n\n"

            f"Document context:\n{context}\n\n"

            f"Question:\n{question}\n\n"

            "Answer:"
        )