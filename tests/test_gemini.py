#day 1
from __future__ import annotations

import pytest
from google import genai

from app.config import settings


@pytest.mark.integration
def test_gemini_connectivity() -> None:
    if not settings.google_api_key:
        pytest.skip("GOOGLE_API_KEY is not configured.")

    client = genai.Client(api_key=settings.google_api_key)
    response = client.models.generate_content(
        model=settings.gemini_model_name,
        contents="Reply with a short confirmation that Gemini is reachable.",
    )

    assert response.text
    print(f"Gemini response: {response.text}")
