"""
Integration tests for PostgreSQL-backed User Portal authentication.

These tests require a running PostgreSQL instance and DATABASE_URL set
in the environment. They are skipped automatically when DATABASE_URL is
absent so they do not block CI runs without a database.

Run specifically with:
    pytest tests/test_pg_auth.py -v -m integration

What is tested
--------------
1.  Database connection succeeds.
2.  Schema creation is idempotent.
3.  New user registration writes a record to PostgreSQL.
4.  Registered user can be retrieved from PostgreSQL after session recreation.
5.  Correct password authenticates successfully.
6.  Incorrect password is rejected.
7.  Empty / None credentials are rejected.
8.  Duplicate registration is rejected with the expected message.
9.  NEEDS_RESET sentinel prevents login for legacy-imported users.
10. Static USER_CREDENTIALS accounts still work (env-var path untouched).
11. AuthManager.register_user and verify_login work end-to-end through PG.
"""

from __future__ import annotations

import os
import pytest

# ---------------------------------------------------------------------------
# Skip entire module when DATABASE_URL is not configured
# ---------------------------------------------------------------------------

_DATABASE_URL = os.getenv("DATABASE_URL", "")
pytestmark = pytest.mark.integration

if not _DATABASE_URL:
    pytest.skip(
        "DATABASE_URL not set — skipping PostgreSQL integration tests.",
        allow_module_level=True,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def db_connection():
    """
    Yield an open psycopg2 connection for the duration of the test module.
    Rolls back any uncommitted changes on teardown.
    """
    import psycopg2

    conn = psycopg2.connect(_DATABASE_URL)
    yield conn
    conn.rollback()
    conn.close()


@pytest.fixture(autouse=True, scope="module")
def ensure_schema(db_connection):
    """Apply the portal_users schema before any test in this module runs."""
    from app.db.init_db import init_schema

    init_schema()


@pytest.fixture()
def cleanup_test_users(db_connection):
    """
    Remove test users created during each test so tests are independent.
    Yields the list of usernames to clean; caller appends to it.
    """
    usernames: list[str] = []
    yield usernames
    if usernames:
        with db_connection.cursor() as cur:
            cur.execute(
                "DELETE FROM portal_users WHERE username = ANY(%s)",
                (usernames,),
            )
        db_connection.commit()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _insert_sentinel_user(db_connection, username: str) -> None:
    """Insert a NEEDS_RESET user directly (simulates init_db legacy import)."""
    with db_connection.cursor() as cur:
        cur.execute(
            "INSERT INTO portal_users (username, password_hash) VALUES (%s, %s)"
            " ON CONFLICT (username) DO NOTHING",
            (username, "NEEDS_RESET"),
        )
    db_connection.commit()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDatabaseConnectivity:
    """Verify the connection layer works correctly."""

    def test_connection_succeeds(self) -> None:
        """check_connection() returns True when DATABASE_URL is valid."""
        from app.db.database import check_connection

        assert check_connection() is True

    def test_get_connection_context_manager(self) -> None:
        """get_connection() yields a live connection and executes a trivial query."""
        from app.db.database import get_connection

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 AS alive")
                row = cur.fetchone()
        assert row is not None
        assert row[0] == 1


class TestSchemaIdempotency:
    """Verify the schema creation is safe to run multiple times."""

    def test_init_schema_is_idempotent(self) -> None:
        """Running init_schema() twice must not raise an error."""
        from app.db.init_db import init_schema

        init_schema()  # second call — must succeed silently
        init_schema()  # third call — still fine

    def test_portal_users_table_exists(self, db_connection) -> None:
        """The portal_users table must exist after init_schema()."""
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = 'portal_users'
                )
                """
            )
            exists = cur.fetchone()[0]
        assert exists is True


class TestRegistration:
    """PostgreSQL user registration via AuthManager."""

    def test_register_new_user_succeeds(self, cleanup_test_users) -> None:
        """Registering a fresh username returns (True, success_message)."""
        from unittest.mock import patch
        from types import SimpleNamespace

        username = "pg_test_register"
        cleanup_test_users.append(username)

        mock_settings = SimpleNamespace(
            user_credentials="",
            database_url=_DATABASE_URL,
            data_dir=None,
        )
        with patch("app.utils.auth.settings", mock_settings):
            from app.utils.auth import AuthManager

            success, msg = AuthManager.register_user(username, "securepassword123")

        assert success is True
        assert "created" in msg.lower()

    def test_registered_user_exists_in_postgresql(
        self, db_connection, cleanup_test_users
    ) -> None:
        """After registration, a row with a bcrypt hash must exist in portal_users."""
        from unittest.mock import patch
        from types import SimpleNamespace

        username = "pg_test_exists"
        cleanup_test_users.append(username)

        mock_settings = SimpleNamespace(
            user_credentials="",
            database_url=_DATABASE_URL,
            data_dir=None,
        )
        with patch("app.utils.auth.settings", mock_settings):
            from app.utils.auth import AuthManager

            AuthManager.register_user(username, "mypassword")

        # Verify record in the database directly
        with db_connection.cursor() as cur:
            cur.execute(
                "SELECT username, password_hash FROM portal_users WHERE username = %s",
                (username,),
            )
            row = cur.fetchone()

        assert row is not None, "User row must exist after registration"
        db_username, password_hash = row
        assert db_username == username
        # Must be a bcrypt hash (starts with $2b$ or $2a$), not plaintext
        assert password_hash.startswith("$2"), (
            f"Expected bcrypt hash, got: {password_hash[:20]}"
        )
        assert password_hash != "NEEDS_RESET"

    def test_duplicate_registration_rejected(self, cleanup_test_users) -> None:
        """Registering an existing username returns (False, already_taken_message)."""
        from unittest.mock import patch
        from types import SimpleNamespace

        username = "pg_test_duplicate"
        cleanup_test_users.append(username)

        mock_settings = SimpleNamespace(
            user_credentials="",
            database_url=_DATABASE_URL,
            data_dir=None,
        )
        with patch("app.utils.auth.settings", mock_settings):
            from app.utils.auth import AuthManager

            AuthManager.register_user(username, "firstpass")
            success, msg = AuthManager.register_user(username, "secondpass")

        assert success is False
        assert "already taken" in msg.lower()

    def test_empty_credentials_rejected(self) -> None:
        """Empty username or password is rejected before hitting the database."""
        from unittest.mock import patch
        from types import SimpleNamespace

        mock_settings = SimpleNamespace(
            user_credentials="",
            database_url=_DATABASE_URL,
            data_dir=None,
        )
        with patch("app.utils.auth.settings", mock_settings):
            from app.utils.auth import AuthManager

            ok1, _ = AuthManager.register_user("", "somepassword")
            ok2, _ = AuthManager.register_user("someuser", "")
        assert ok1 is False
        assert ok2 is False


class TestLogin:
    """PostgreSQL password verification via AuthManager."""

    def test_correct_password_authenticates(self, cleanup_test_users) -> None:
        """
        Full end-to-end: register → close session → reopen → verify login.
        This proves PostgreSQL persistence survives session recreation.
        """
        from unittest.mock import patch
        from types import SimpleNamespace

        username = "pg_test_login_ok"
        password = "correct_password_123"
        cleanup_test_users.append(username)

        mock_settings = SimpleNamespace(
            user_credentials="",
            database_url=_DATABASE_URL,
            data_dir=None,
        )

        # Registration (first "session")
        with patch("app.utils.auth.settings", mock_settings):
            from app.utils.auth import AuthManager

            ok, _ = AuthManager.register_user(username, password)
        assert ok is True

        # Login (second "session" — simulated by re-importing with same mock)
        with patch("app.utils.auth.settings", mock_settings):
            from app.utils.auth import AuthManager as AM2

            result = AM2.verify_login(username, password)
        assert result is True

    def test_incorrect_password_rejected(self, cleanup_test_users) -> None:
        """Wrong password must be rejected."""
        from unittest.mock import patch
        from types import SimpleNamespace

        username = "pg_test_login_bad"
        cleanup_test_users.append(username)

        mock_settings = SimpleNamespace(
            user_credentials="",
            database_url=_DATABASE_URL,
            data_dir=None,
        )
        with patch("app.utils.auth.settings", mock_settings):
            from app.utils.auth import AuthManager

            AuthManager.register_user(username, "correct_pw")
            result = AuthManager.verify_login(username, "wrong_pw")
        assert result is False

    def test_nonexistent_user_rejected(self) -> None:
        """Login for a username that does not exist must return False."""
        from unittest.mock import patch
        from types import SimpleNamespace

        mock_settings = SimpleNamespace(
            user_credentials="",
            database_url=_DATABASE_URL,
            data_dir=None,
        )
        with patch("app.utils.auth.settings", mock_settings):
            from app.utils.auth import AuthManager

            result = AuthManager.verify_login("no_such_user_xyz", "anypassword")
        assert result is False

    def test_none_credentials_rejected(self) -> None:
        """None username or password must return False without hitting the database."""
        from unittest.mock import patch
        from types import SimpleNamespace

        mock_settings = SimpleNamespace(
            user_credentials="",
            database_url=_DATABASE_URL,
            data_dir=None,
        )
        with patch("app.utils.auth.settings", mock_settings):
            from app.utils.auth import AuthManager

            assert AuthManager.verify_login(None, "pw") is False
            assert AuthManager.verify_login("user", None) is False
            assert AuthManager.verify_login(None, None) is False

    def test_needs_reset_sentinel_blocks_login(
        self, db_connection, cleanup_test_users
    ) -> None:
        """
        A user imported from the legacy JSON with NEEDS_RESET must not be able
        to log in even with a correctly guessed password.
        """
        from unittest.mock import patch
        from types import SimpleNamespace

        username = "pg_test_needs_reset"
        cleanup_test_users.append(username)

        _insert_sentinel_user(db_connection, username)

        mock_settings = SimpleNamespace(
            user_credentials="",
            database_url=_DATABASE_URL,
            data_dir=None,
        )
        with patch("app.utils.auth.settings", mock_settings):
            from app.utils.auth import AuthManager

            result = AuthManager.verify_login(username, "anypassword")
        assert result is False


class TestStaticCredentialsUnaffected:
    """Static USER_CREDENTIALS env-var accounts must continue to work."""

    def test_static_user_login_still_works(self) -> None:
        """Static admin user from USER_CREDENTIALS passes verification."""
        from unittest.mock import patch
        from types import SimpleNamespace

        mock_settings = SimpleNamespace(
            user_credentials="admin:admin123",
            database_url=_DATABASE_URL,
            data_dir=None,
        )
        with patch("app.utils.auth.settings", mock_settings):
            from app.utils.auth import AuthManager

            assert AuthManager.verify_login("admin", "admin123") is True
            assert AuthManager.verify_login("admin", "wrongpass") is False

    def test_static_username_cannot_be_registered(self) -> None:
        """A portal user cannot shadow a static admin account."""
        from unittest.mock import patch
        from types import SimpleNamespace

        mock_settings = SimpleNamespace(
            user_credentials="admin:admin123",
            database_url=_DATABASE_URL,
            data_dir=None,
        )
        with patch("app.utils.auth.settings", mock_settings):
            from app.utils.auth import AuthManager

            ok, msg = AuthManager.register_user("admin", "newpassword")
        assert ok is False
        assert "already taken" in msg.lower()


class TestPasswordHashSecurity:
    """Verify stored password values are bcrypt hashes, never plaintext."""

    def test_stored_value_is_not_plaintext(
        self, db_connection, cleanup_test_users
    ) -> None:
        """The value in password_hash must not equal the original password."""
        from unittest.mock import patch
        from types import SimpleNamespace

        username = "pg_test_hash_check"
        password = "plaintext_password"
        cleanup_test_users.append(username)

        mock_settings = SimpleNamespace(
            user_credentials="",
            database_url=_DATABASE_URL,
            data_dir=None,
        )
        with patch("app.utils.auth.settings", mock_settings):
            from app.utils.auth import AuthManager

            AuthManager.register_user(username, password)

        with db_connection.cursor() as cur:
            cur.execute(
                "SELECT password_hash FROM portal_users WHERE username = %s",
                (username,),
            )
            row = cur.fetchone()

        assert row is not None
        stored = row[0]
        assert stored != password, "Password must not be stored as plaintext"
        assert stored.startswith("$2"), "Password must be stored as a bcrypt hash"
