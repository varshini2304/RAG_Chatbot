"""Centralized user-facing messages for localization (multilingual support)."""

MESSAGES = {
    "en": {
        "insufficient_information": "The uploaded documents do not contain sufficient information to answer this question.",
        "empty_context": "The uploaded documents do not contain sufficient information to answer this question.",
        "retrieval_failed": "Retrieval failed. Try again or re-upload documents if the problem persists.",
        "rate_limited": "The AI provider is temporarily rate-limited. Please wait a moment and try again.",
    },
    "ja": {
        "insufficient_information": "アップロードされたドキュメントには、この質問に回答するための十分な情報がありません。",
        "empty_context": "アップロードされたドキュメントには、この質問に回答するための十分な情報がありません。",
        "retrieval_failed": "検索に失敗しました。再試行するか、問題が解決しない場合はドキュメントを再アップロードしてください。",
        "rate_limited": "AIプロバイダーが一時的に速度制限されています。しばらく待ってからもう一度お試しください。",
    },
}


def get_message(key: str, lang: str = "en") -> str:
    """Retrieve localized message for key and language.

    Defaults to English if the language is not supported or the key is missing.
    """
    lang_messages = MESSAGES.get(lang, MESSAGES["en"])
    return lang_messages.get(key, MESSAGES["en"].get(key, ""))
