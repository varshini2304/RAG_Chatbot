"""Session-wide pytest configuration and global settings overrides."""

from __future__ import annotations

import pytest

from app.config import settings


@pytest.fixture(autouse=True, scope="session")
def use_legacy_model_for_testing() -> None:
   
    object.__setattr__(settings, "embedding_model_name", "all-MiniLM-L6-v2")
    object.__setattr__(settings, "embedding_dimension", 384)
    object.__setattr__(settings, "retrieval_min_similarity", 0.0)
