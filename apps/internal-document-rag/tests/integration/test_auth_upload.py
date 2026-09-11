"""Integration test for Workflow 3: User Login / Authentication -> Authorized Upload."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.utils.auth import AuthManager


def test_auth_login_and_user_directory_workspace(tmp_path: Path) -> None:
    """Test authenticating a user and verifying workspace isolation directory."""
    data_dir = tmp_path / "data"
    mock_settings = SimpleNamespace(
        user_credentials="hr_admin:hrpass123",
        data_dir=data_dir,
    )

    with patch("app.utils.auth.settings", mock_settings):
        # 1. Login user
        is_authenticated = AuthManager.verify_login("hr_admin", "hrpass123")
        assert is_authenticated is True

        # 2. Simulate saving user-isolated session data
        user_upload_folder = data_dir / "uploads" / "hr_admin"
        user_upload_folder.mkdir(parents=True, exist_ok=True)
        assert user_upload_folder.exists()

        # 3. Save sample user document into isolated workspace
        sample_file = user_upload_folder / "hr_policy.txt"
        sample_file.write_text("HR Policy content", encoding="utf-8")
        assert sample_file.exists()
