"""Unit tests for the simple authentication manager."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.utils.auth import AuthManager


def test_auth_manager_parses_credentials(tmp_path: Path) -> None:
    """AuthManager should correctly parse comma-separated username:password configurations."""
    mock_settings = SimpleNamespace(
        user_credentials="user1:pass1,user2:pass2",
        data_dir=tmp_path,
        database_url=None,  # no PG — exercises JSON fallback path
    )
    with patch("app.utils.auth.settings", mock_settings):
        users = AuthManager.get_users_dict()
        assert users == {"user1": "pass1", "user2": "pass2"}


def test_auth_manager_handles_malformed_credentials(tmp_path: Path) -> None:
    """Malformed credentials (missing colon) should be skipped gracefully."""
    mock_settings = SimpleNamespace(
        user_credentials="user1:pass1,malformed_item,user2:pass2",
        data_dir=tmp_path,
        database_url=None,
    )
    with patch("app.utils.auth.settings", mock_settings):
        users = AuthManager.get_users_dict()
        assert users == {"user1": "pass1", "user2": "pass2"}


def test_auth_manager_verify_login_succeeds(tmp_path: Path) -> None:
    """Matching username and password should pass verification."""
    mock_settings = SimpleNamespace(
        user_credentials="admin:admin123",
        data_dir=tmp_path,
        database_url=None,
    )
    with patch("app.utils.auth.settings", mock_settings):
        assert AuthManager.verify_login("admin", "admin123") is True
        assert AuthManager.verify_login(" admin ", " admin123 ") is True  # Strip check


def test_auth_manager_verify_login_fails(tmp_path: Path) -> None:
    """Invalid username or password combinations must fail verification."""
    mock_settings = SimpleNamespace(
        user_credentials="admin:admin123",
        data_dir=tmp_path,
        database_url=None,  # forces JSON fallback; wronguser won't be found anywhere
    )
    with patch("app.utils.auth.settings", mock_settings):
        assert AuthManager.verify_login("admin", "wrongpassword") is False
        assert AuthManager.verify_login("wronguser", "admin123") is False
        assert AuthManager.verify_login("", "admin123") is False
        assert AuthManager.verify_login("admin", "") is False
        assert AuthManager.verify_login(None, "admin123") is False


def test_auth_manager_dynamic_registration(tmp_path: Path) -> None:
    """AuthManager should support user self-registration to local storage."""
    mock_settings = SimpleNamespace(
        user_credentials="admin:admin123",
        data_dir=tmp_path / "data",
        database_url=None,  # forces JSON fallback path for this unit test
    )

    with patch("app.utils.auth.settings", mock_settings):
        # Test registering new username
        success, msg = AuthManager.register_user("varsh", "mypassword")
        assert success is True
        assert msg == "Account created successfully!"

        reg_file = mock_settings.data_dir / "registered_users.json"
        assert reg_file.exists()

        # Test verifying login of dynamically registered user
        assert AuthManager.verify_login("varsh", "mypassword") is True

        # Test registering existing username fails
        success, msg = AuthManager.register_user("admin", "somepass")
        assert success is False
        assert "already taken" in msg

        success, msg = AuthManager.register_user("varsh", "somepass")
        assert success is False
        assert "already taken" in msg
