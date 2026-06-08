"""Gemini connectivity test for local environment validation.

This test verifies that the configured Gemini API key can reach the Gemini API
and returns a model response. It is intended for local setup validation and
requires `GOOGLE_API_KEY` to be present in the environment or `.env` file.
"""

from __future__ import annotations

import pytest
from google import genai

from app.config import settings


@pytest.mark.integration
def test_gemini_connectivity() -> None:
    """Verify Gemini API connectivity using the configured API key."""
    if not settings.google_api_key:
        pytest.skip("GOOGLE_API_KEY is not configured.")

    client = genai.Client(api_key=settings.google_api_key)
    response = client.models.generate_content(
        model=settings.gemini_model_name,
        contents="Reply with a short confirmation that Gemini is reachable.",
    )

    assert response.text
    print(f"Gemini response: {response.text}")
