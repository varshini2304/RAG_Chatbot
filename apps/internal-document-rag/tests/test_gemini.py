# day 1
from __future__ import annotations

import pytest
from google import genai
from google.genai import errors

from app.config import settings


@pytest.mark.integration
def test_gemini_connectivity() -> None:
    if (
        not settings.google_api_key
        or settings.google_api_key == "your_google_api_key_here"
    ):
        pytest.skip("GOOGLE_API_KEY is not configured.")

    client = genai.Client(api_key=settings.google_api_key)
    try:
        response = client.models.generate_content(
            model=settings.gemini_model_name,
            contents="Reply with a short confirmation that Gemini is reachable.",
        )
    except (errors.ClientError, errors.ServerError, Exception) as exc:
        if any(
            err in str(exc)
            for err in ("401", "429", "503", "UNAUTHENTICATED", "RESOURCE_EXHAUSTED", "UNAVAILABLE")
        ):
            pytest.skip(f"Gemini API unavailable, quota exhausted, or unauthenticated: {exc}")
        raise

    assert response.text
    print(f"Gemini response: {response.text}")
