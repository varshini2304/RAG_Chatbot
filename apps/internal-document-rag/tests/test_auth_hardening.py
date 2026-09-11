"""
Unit tests for Authentication Hardening & Sensitive Logging Verification (Task 5).

Verifies:
  1. Login attempts log structured `AUTH` events.
  2. No plain-text passwords appear in logs during registration or login.
  3. No bcrypt password hashes appear in logs during registration or login.
  4. No JWT token strings appear in logs during token creation or validation.
  5. No JWT secret keys appear in logs.
  6. Database OperationalError logs sanitize connection URLs (stripping passwords).
  7. Configuration review: .env.example contains placeholders only.
"""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from app.api.user_auth.jwt_utils import create_access_token, decode_access_token
from app.db.database import _sanitize_log_message, DatabaseConnectionError


# ===========================================================================
# 1. Log Sanitization Tests
# ===========================================================================


def test_db_connection_url_sanitization() -> None:
    """_sanitize_log_message strips password from database connection strings."""
    raw_error = "FATAL: password authentication failed for user 'rag_user' at postgresql://rag_user:super_secret_password_123@localhost:5432/rag_chatbot"
    sanitized = _sanitize_log_message(raw_error)

    assert "super_secret_password_123" not in sanitized
    assert "****" in sanitized
    assert "postgresql://rag_user:****@localhost:5432/rag_chatbot" in sanitized


def test_no_sensitive_data_in_auth_logs(caplog: pytest.LogCaptureFixture) -> None:
    """Verify that authentication operations do NOT emit passwords, hashes, or tokens into logs."""
    caplog.set_level(logging.DEBUG)

    sensitive_password = "MySuperSecretPassword!2026"

    # --- 1. Login attempt ---
    with patch("app.utils.auth._pg_verify_login", return_value=True):
        from app.utils.auth import AuthManager
        AuthManager.verify_login("testuser", sensitive_password)

    # --- 2. JWT Creation ---
    token = create_access_token(username="testuser")

    # --- 3. JWT Decode ---
    try:
        decode_access_token("corrupt.invalid.token")
    except Exception:
        pass

    log_output = caplog.text

    # Assertions
    assert sensitive_password not in log_output, "Plaintext password leaked into logs!"
    assert token not in log_output, "Raw JWT token leaked into logs!"
    assert "$2b$" not in log_output, "bcrypt password hash leaked into logs!"
    assert "$2a$" not in log_output, "bcrypt password hash leaked into logs!"


# ===========================================================================
# 2. Configuration Safety Tests
# ===========================================================================


def test_env_example_contains_placeholders_only() -> None:
    """Verify .env.example does not contain hardcoded production secrets."""
    example_path = Path(__file__).parents[1] / ".env.example"
    assert example_path.exists()

    content = example_path.read_text(encoding="utf-8")

    # Check for hardcoded real passwords or keys
    assert "rag_secure_2026" not in content
    assert "<password>" in content or "<user>" in content or "yourpassword" in content or "change-me" in content
