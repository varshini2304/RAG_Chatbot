"""
Comprehensive unit and integration tests for JWT Generation and Validation (Task 3).

Tests cover:
  - Valid credentials generate a JWT token
  - Correct `sub` claim
  - Correct `type="user_portal"` claim
  - `exp` claim exists and is valid
  - Valid JWT accepted on protected endpoint (/api/v1/user-auth/me)
  - Invalid signature is rejected
  - Expired JWT is rejected
  - Malformed JWT is rejected
  - Missing token is rejected
  - Tampered payload is rejected
  - Wrong credentials do NOT generate a JWT
  - Nonexistent/deleted user JWT is rejected
  - Admin `rac_*` token is rejected on User Portal endpoints
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient
from jose import jwt

from app.api.api_app import app
from app.api.user_auth.jwt_utils import create_access_token, decode_access_token
from app.config import settings

client = TestClient(app, raise_server_exceptions=False)

REGISTER_URL = "/api/v1/user-auth/register"
LOGIN_URL = "/api/v1/user-auth/login"
ME_URL = "/api/v1/user-auth/me"


# ===========================================================================
# 1. JWT Generation & Claims
# ===========================================================================


def test_valid_credentials_generate_jwt() -> None:
    """Successful login returns 200 with a valid JWT token."""
    with patch("app.api.routers.user_auth.AuthManager") as mock_auth:
        mock_auth.verify_login.return_value = True
        response = client.post(
            LOGIN_URL,
            json={"username": "validuser", "password": "validpassword"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "token" in data
    assert data["token_type"] == "bearer"


def test_jwt_claims_structure() -> None:
    """Generated JWT contains sub, exp, and type='user_portal' claims."""
    token = create_access_token(username="testuser")
    payload = decode_access_token(token)

    assert payload["sub"] == "testuser"
    assert payload["type"] == "user_portal"
    assert "exp" in payload
    assert isinstance(payload["exp"], int)


def test_wrong_credentials_do_not_generate_jwt() -> None:
    """Invalid credentials return 401 without generating a token."""
    with patch("app.api.routers.user_auth.AuthManager") as mock_auth:
        mock_auth.verify_login.return_value = False
        response = client.post(
            LOGIN_URL,
            json={"username": "validuser", "password": "wrongpassword"},
        )
    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert "token" not in data


# ===========================================================================
# 2. JWT Protected Route Validation
# ===========================================================================


def test_valid_jwt_accepted_on_protected_route() -> None:
    """A valid JWT for an existing user is accepted with 200 OK."""
    with patch("app.utils.auth.AuthManager.user_exists", return_value=True):
        token = create_access_token(username="alice")
        response = client.get(
            ME_URL,
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["username"] == "alice"


def test_invalid_signature_rejected() -> None:
    """JWT signed with a different secret key is rejected with 401."""
    # Create token using a fake secret
    fake_token = jwt.encode(
        {"sub": "alice", "type": "user_portal"},
        "wrong-secret-key-12345678901234567890",
        algorithm="HS256",
    )
    with patch("app.utils.auth.AuthManager.user_exists", return_value=True):
        response = client.get(
            ME_URL,
            headers={"Authorization": f"Bearer {fake_token}"},
        )
    assert response.status_code == 401
    assert "WWW-Authenticate" in response.headers


def test_expired_jwt_rejected() -> None:
    """Expired JWT is rejected with 401."""
    expired_token = create_access_token(
        username="alice",
        expires_delta=timedelta(seconds=-10),  # expired 10 seconds ago
    )
    with patch("app.utils.auth.AuthManager.user_exists", return_value=True):
        response = client.get(
            ME_URL,
            headers={"Authorization": f"Bearer {expired_token}"},
        )
    assert response.status_code == 401


def test_malformed_jwt_rejected() -> None:
    """Malformed token string is rejected with 401."""
    response = client.get(
        ME_URL,
        headers={"Authorization": "Bearer not.a.real.jwt.token"},
    )
    assert response.status_code == 401


def test_missing_token_rejected() -> None:
    """Request without Authorization header is rejected with 401 or 403."""
    response = client.get(ME_URL)
    assert response.status_code in (401, 403)


def test_tampered_payload_rejected() -> None:
    """Modifying the token payload invalidates the signature and returns 401."""
    token = create_access_token(username="alice")
    parts = token.split(".")
    # Tamper with the middle part (payload)
    tampered_token = f"{parts[0]}.e30.{parts[2]}"
    with patch("app.utils.auth.AuthManager.user_exists", return_value=True):
        response = client.get(
            ME_URL,
            headers={"Authorization": f"Bearer {tampered_token}"},
        )
    assert response.status_code == 401


def test_nonexistent_or_deleted_user_jwt_rejected() -> None:
    """A validly signed JWT for a deleted or nonexistent user is rejected with 401."""
    token = create_access_token(username="deleted_user")
    with patch("app.utils.auth.AuthManager.user_exists", return_value=False):
        response = client.get(
            ME_URL,
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 401


def test_admin_token_format_rejected() -> None:
    """Admin console token format (rac_*) is rejected on User Portal endpoints."""
    response = client.get(
        ME_URL,
        headers={"Authorization": "Bearer rac_a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"},
    )
    assert response.status_code == 401
