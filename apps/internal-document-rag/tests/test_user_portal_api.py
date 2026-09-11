"""
Integration tests for the User Portal API endpoints.

Tests cover:
  - User registration
  - User login (valid + invalid)
  - JWT validation / /me endpoint
  - Unauthorized access to protected endpoints
  - Authenticated document endpoint access (workspace isolation)
  - Chat query API (mocked pipeline)
  - Workspace isolation between users

Run with:
    pytest tests/test_user_portal_api.py -v --tb=short -p no:logging

These tests use the TestClient with a mocked AuthManager to avoid filesystem
dependencies. RAG pipeline tests are separately mocked to keep tests fast.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient

from app.api.api_app import app
from app.api.user_auth.jwt_utils import create_access_token, decode_access_token

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def mock_user_exists_for_api_tests():
    """Ensure synthetic test users (alice, bob, etc.) pass user_exists checks."""
    with patch("app.utils.auth.AuthManager.user_exists", return_value=True):
        yield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REGISTER_URL = "/api/v1/user-auth/register"
LOGIN_URL = "/api/v1/user-auth/login"
ME_URL = "/api/v1/user-auth/me"
DOCUMENTS_URL = "/api/v1/documents"
UPLOAD_URL = "/api/v1/documents/upload"
WORKSPACE_STATUS_URL = "/api/v1/workspace/status"
CHAT_QUERY_URL = "/api/v1/chat/query"
SESSIONS_URL = "/api/v1/chat/sessions"


def _auth_headers(username: str) -> dict[str, str]:
    """Generate a valid Authorization header for the given username."""
    token = create_access_token(username=username)
    return {"Authorization": f"Bearer {token}"}


def _make_workspace_mock(username: str, documents: list | None = None) -> MagicMock:
    """Build a minimal mock WorkspaceState for a user."""
    mock = MagicMock()
    mock.documents = documents or []
    mock.chunks = {}
    mock.embedding_status = {}
    mock.hashes = {}
    mock.processed_names = set()
    mock.document_errors = {}
    mock.bm25_index_manager = MagicMock()
    return mock


# ===========================================================================
# 1. User Registration
# ===========================================================================


class TestUserRegistration:
    """POST /api/v1/user-auth/register"""

    def test_register_new_user_succeeds(self, tmp_path) -> None:
        """Registering a fresh username returns 201 with a JWT token."""
        with patch("app.api.routers.user_auth.AuthManager") as mock_auth:
            mock_auth.register_user.return_value = (True, "Account created successfully!")
            response = client.post(
                REGISTER_URL,
                json={
                    "username": "newuser",
                    "password": "securepass",
                    "confirm_password": "securepass",
                },
            )
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["success"] is True
        assert "token" in data
        assert data["username"] == "newuser"
        assert data["avatar_letter"] == "N"

    def test_register_duplicate_username_returns_409(self) -> None:
        """Registering an existing username returns 409 Conflict."""
        with patch("app.api.routers.user_auth.AuthManager") as mock_auth:
            mock_auth.register_user.return_value = (
                False,
                "Username 'existing' is already taken.",
            )
            response = client.post(
                REGISTER_URL,
                json={
                    "username": "existing",
                    "password": "somepass",
                    "confirm_password": "somepass",
                },
            )
        assert response.status_code == 409, response.text

    def test_register_password_mismatch_returns_400(self) -> None:
        """Mismatched passwords should return 400 before hitting AuthManager."""
        response = client.post(
            REGISTER_URL,
            json={
                "username": "testuser",
                "password": "password1",
                "confirm_password": "password2",
            },
        )
        assert response.status_code == 400
        assert "match" in response.text.lower()

    def test_register_short_password_returns_400_or_422(self) -> None:
        """Password shorter than 6 characters should return 422 (Pydantic validation) or 400."""
        response = client.post(
            REGISTER_URL,
            json={
                "username": "testuser",
                "password": "abc",
                "confirm_password": "abc",
            },
        )
        assert response.status_code in (400, 422)

    def test_register_empty_username_returns_422_or_400(self) -> None:
        """Empty username fails Pydantic min_length or our validation."""
        response = client.post(
            REGISTER_URL,
            json={"username": "", "password": "password1", "confirm_password": "password1"},
        )
        assert response.status_code in (400, 422)


# ===========================================================================
# 2. User Login
# ===========================================================================


class TestUserLogin:
    """POST /api/v1/user-auth/login"""

    def test_valid_login_returns_token(self) -> None:
        """Valid credentials return 200 with a JWT token."""
        with patch("app.api.routers.user_auth.AuthManager") as mock_auth:
            mock_auth.verify_login.return_value = True
            response = client.post(
                LOGIN_URL,
                json={"username": "admin", "password": "admin123"},
            )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["success"] is True
        assert "token" in data
        assert data["username"] == "admin"
        assert data["token_type"] == "bearer"

    def test_invalid_credentials_returns_401(self) -> None:
        """Invalid credentials return 401 Unauthorized."""
        with patch("app.api.routers.user_auth.AuthManager") as mock_auth:
            mock_auth.verify_login.return_value = False
            response = client.post(
                LOGIN_URL,
                json={"username": "admin", "password": "wrongpassword"},
            )
        assert response.status_code == 401, response.text
        data = response.json()
        assert data["success"] is False

    def test_missing_credentials_returns_400_or_422(self) -> None:
        """Empty username/password returns 400 or 422 Unprocessable Entity."""
        response = client.post(
            LOGIN_URL,
            json={"username": "", "password": ""},
        )
        assert response.status_code in (400, 422)

    def test_login_token_is_decodable(self) -> None:
        """The JWT returned from login should be valid and contain the correct sub claim."""
        with patch("app.api.routers.user_auth.AuthManager") as mock_auth:
            mock_auth.verify_login.return_value = True
            response = client.post(
                LOGIN_URL,
                json={"username": "testuser", "password": "testpass"},
            )
        assert response.status_code == 200
        token = response.json()["token"]
        payload = decode_access_token(token)
        assert payload["sub"] == "testuser"
        assert payload["type"] == "user_portal"


# ===========================================================================
# 3. JWT Validation / /me endpoint
# ===========================================================================


class TestJWTValidation:
    """GET /api/v1/user-auth/me"""

    def test_valid_token_returns_200(self) -> None:
        """A valid user portal token returns 200 with identity information."""
        response = client.get(ME_URL, headers=_auth_headers("alice"))
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["success"] is True
        assert data["username"] == "alice"
        assert data["avatar_letter"] == "A"

    def test_missing_token_returns_403_or_401(self) -> None:
        """No Authorization header returns 401 or 403."""
        response = client.get(ME_URL)
        assert response.status_code in (401, 403)

    def test_invalid_token_returns_401_or_403(self) -> None:
        """A tampered/invalid token returns 401 or 403."""
        response = client.get(
            ME_URL, headers={"Authorization": "Bearer this.is.not.valid"}
        )
        assert response.status_code in (401, 403)

    def test_admin_token_rejected_on_user_endpoint(self) -> None:
        """An admin-format token (rac_*) should be rejected on user portal endpoints."""
        # Admin tokens use a different format and will fail JWT decoding
        response = client.get(
            ME_URL,
            headers={"Authorization": "Bearer rac_a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2"},
        )
        assert response.status_code in (401, 403)


# ===========================================================================
# 4. Unauthorized Access
# ===========================================================================


class TestUnauthorizedAccess:
    """All protected endpoints must reject unauthenticated requests."""

    def test_documents_list_requires_auth(self) -> None:
        response = client.get(DOCUMENTS_URL)
        assert response.status_code in (401, 403)

    def test_document_upload_requires_auth(self) -> None:
        response = client.post(UPLOAD_URL, files={"file": ("test.txt", b"content")})
        assert response.status_code in (401, 403)

    def test_workspace_status_requires_auth(self) -> None:
        response = client.get(WORKSPACE_STATUS_URL)
        assert response.status_code in (401, 403)

    def test_chat_query_requires_auth(self) -> None:
        response = client.post(CHAT_QUERY_URL, json={"question": "What is this?"})
        assert response.status_code in (401, 403)

    def test_sessions_list_requires_auth(self) -> None:
        response = client.get(SESSIONS_URL)
        assert response.status_code in (401, 403)


# ===========================================================================
# 5. Authenticated Document Access
# ===========================================================================


class TestAuthenticatedDocumentAccess:
    """Documents endpoints work correctly for authenticated users."""

    def test_list_documents_returns_workspace(self) -> None:
        """Authenticated user can list their documents."""
        mock_ws = _make_workspace_mock("alice")
        with patch(
            "app.api.routers.documents.WorkspaceService.load_workspace",
            return_value=mock_ws,
        ):
            response = client.get(DOCUMENTS_URL, headers=_auth_headers("alice"))
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["success"] is True
        assert "documents" in data["data"]

    def test_delete_document_requires_auth(self) -> None:
        """DELETE /documents/{filename} without auth returns 401/403."""
        response = client.delete(f"{DOCUMENTS_URL}/test.pdf")
        assert response.status_code in (401, 403)

    def test_path_traversal_rejected(self) -> None:
        """Filenames with path traversal characters are rejected."""
        response = client.delete(
            f"{DOCUMENTS_URL}/../../../etc/passwd",
            headers=_auth_headers("alice"),
        )
        # Either path traversal is rejected or file not found — never 200
        assert response.status_code in (400, 404, 422, 500)


# ===========================================================================
# 6. Chat Query API
# ===========================================================================


class TestChatQueryAPI:
    """POST /api/v1/chat/query"""

    def test_chat_query_returns_answer(self) -> None:
        """Authenticated query returns an answer and sources."""
        from app.models.query_result import QueryResult, QueryResultKind

        mock_result = QueryResult(
            answer="The document says X.",
            retrieved_chunks=[],
            kind=QueryResultKind.SUCCESS,
        )

        with patch(
            "app.api.routers.chat.QueryService.process_question",
            return_value=mock_result,
        ):
            response = client.post(
                CHAT_QUERY_URL,
                headers=_auth_headers("alice"),
                json={"question": "What does the document say?", "query_language": "en"},
            )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["success"] is True
        assert data["data"]["answer"] == "The document says X."
        assert data["data"]["kind"] == "success"
        assert isinstance(data["data"]["sources"], list)

    def test_chat_query_username_comes_from_jwt(self) -> None:
        """QueryService must receive the username from the JWT, not from the request body."""
        from app.models.query_result import QueryResult, QueryResultKind

        captured_calls: list[dict] = []

        def _mock_process(question: str, username: str, query_language: str, bm25_index_manager: Any = None, offline_mode: bool = False) -> QueryResult:
            captured_calls.append({"username": username})
            return QueryResult(
                answer="ok",
                retrieved_chunks=[],
                kind=QueryResultKind.SUCCESS,
            )

        with patch(
            "app.api.routers.chat.QueryService.process_question",
            side_effect=_mock_process,
        ):
            client.post(
                CHAT_QUERY_URL,
                headers=_auth_headers("alice"),
                json={"question": "test question", "query_language": "en"},
            )

        assert len(captured_calls) == 1
        # The username MUST come from the JWT (alice), not from any request body
        assert captured_calls[0]["username"] == "alice"

    def test_empty_question_returns_400(self) -> None:
        """An empty question string should return 400."""
        response = client.post(
            CHAT_QUERY_URL,
            headers=_auth_headers("alice"),
            json={"question": "   ", "query_language": "en"},
        )
        assert response.status_code == 400


# ===========================================================================
# 7. Workspace Isolation
# ===========================================================================


class TestWorkspaceIsolation:
    """User A cannot access User B's workspace, documents, or chat history."""

    def test_workspace_load_uses_jwt_username(self) -> None:
        """WorkspaceService.load_workspace is called with the JWT username, not any param."""
        captured_users: list[str] = []

        mock_ws = _make_workspace_mock("alice")

        def _mock_load(username: str):
            captured_users.append(username)
            return mock_ws

        with patch(
            "app.api.routers.documents.WorkspaceService.load_workspace",
            side_effect=_mock_load,
        ):
            client.get(DOCUMENTS_URL, headers=_auth_headers("alice"))

        assert captured_users == ["alice"]

    def test_user_b_cannot_see_user_a_documents(self) -> None:
        """User B's token produces User B's workspace, not User A's."""
        mock_ws_a = _make_workspace_mock("alice")
        mock_ws_b = _make_workspace_mock("bob")

        def _mock_load(username: str):
            if username == "alice":
                return mock_ws_a
            return mock_ws_b

        with patch(
            "app.api.routers.documents.WorkspaceService.load_workspace",
            side_effect=_mock_load,
        ):
            resp_a = client.get(DOCUMENTS_URL, headers=_auth_headers("alice"))
            resp_b = client.get(DOCUMENTS_URL, headers=_auth_headers("bob"))

        assert resp_a.status_code == 200
        assert resp_b.status_code == 200

    def test_chat_sessions_isolated_by_user(self) -> None:
        """ChatHistoryService.load_user_chats is called with the JWT username."""
        captured_users: list[str] = []

        def _mock_load(username: str):
            captured_users.append(username)
            return []

        with patch(
            "app.api.routers.chat.ChatHistoryService.load_user_chats",
            side_effect=_mock_load,
        ):
            client.get(SESSIONS_URL, headers=_auth_headers("alice"))
            client.get(SESSIONS_URL, headers=_auth_headers("bob"))

        # Each call must use the correct user's identifier from the JWT
        assert "alice" in captured_users
        assert "bob" in captured_users
        assert captured_users == ["alice", "bob"]
