"""Unit tests for the authentication and user registration module."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.utils.auth import AuthManager


def test_auth_manager_parses_valid_credentials(tmp_path: Path) -> None:
    """AuthManager should correctly parse username:password pairs."""
    mock_settings = SimpleNamespace(
        user_credentials="admin:admin123,user1:pass123",
        data_dir=tmp_path,
    )
    with patch("app.utils.auth.settings", mock_settings):
        users = AuthManager.get_users_dict()
        assert users == {"admin": "admin123", "user1": "pass123"}


def test_auth_manager_handles_malformed_credentials(tmp_path: Path) -> None:
    """Malformed credential strings without colons should be ignored safely."""
    mock_settings = SimpleNamespace(
        user_credentials="admin:admin123,invalid_string,user2:pass456",
        data_dir=tmp_path,
    )
    with patch("app.utils.auth.settings", mock_settings):
        users = AuthManager.get_users_dict()
        assert "admin" in users
        assert "user2" in users
        assert "invalid_string" not in users


def test_verify_login_success_cases(tmp_path: Path) -> None:
    """Valid credentials and padded whitespace inputs should succeed."""
    mock_settings = SimpleNamespace(
        user_credentials="admin:admin123,hr_user:hrpass123",
        data_dir=tmp_path,
    )
    with patch("app.utils.auth.settings", mock_settings):
        assert AuthManager.verify_login("admin", "admin123") is True
        assert AuthManager.verify_login(" admin ", " admin123 ") is True
        assert AuthManager.verify_login("hr_user", "hrpass123") is True


@pytest.mark.parametrize(
    "username,password",
    [
        ("admin", "wrong_pass"),
        ("non_existent_user", "admin123"),
        ("", "admin123"),
        ("admin", ""),
        (None, "admin123"),
        ("admin", None),
    ],
)
def test_verify_login_failure_cases(
    tmp_path: Path, username: str | None, password: str | None
) -> None:
    """Invalid, empty, or missing parameters must fail verification."""
    mock_settings = SimpleNamespace(
        user_credentials="admin:admin123",
        data_dir=tmp_path,
    )
    with patch("app.utils.auth.settings", mock_settings):
        assert AuthManager.verify_login(username, password) is False


def test_user_registration_lifecycle(tmp_path: Path) -> None:
    """Test dynamic user registration, duplicate checks, and validation."""
    data_directory = tmp_path / "data"
    data_directory.mkdir(parents=True, exist_ok=True)
    mock_settings = SimpleNamespace(
        user_credentials="admin:admin123",
        data_dir=data_directory,
    )

    with patch("app.utils.auth.settings", mock_settings):
        # 1. Register new user successfully
        success, message = AuthManager.register_user("new_dev", "securepass123")
        assert success is True
        assert "created successfully" in message.lower()

        # 2. Login as newly registered user
        assert AuthManager.verify_login("new_dev", "securepass123") is True

        # 3. Reject duplicate username
        success_dup, msg_dup = AuthManager.register_user("new_dev", "otherpass")
        assert success_dup is False
        assert "already taken" in msg_dup.lower()

        # 4. Reject registration of configured admin
        success_admin, msg_admin = AuthManager.register_user("admin", "otherpass")
        assert success_admin is False
        assert "already taken" in msg_admin.lower()


def test_user_registration_empty_inputs(tmp_path: Path) -> None:
    """Empty usernames or passwords should be rejected."""
    mock_settings = SimpleNamespace(
        user_credentials="admin:admin123",
        data_dir=tmp_path / "data",
    )
    with patch("app.utils.auth.settings", mock_settings):
        success, msg = AuthManager.register_user("", "123456")
        assert success is False
        assert "cannot be empty" in msg.lower()

        success_pass, msg_pass = AuthManager.register_user("validuser", "   ")
        assert success_pass is False
        assert "cannot be empty" in msg_pass.lower()
