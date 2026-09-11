"""
Authentication helpers for User Portal login and registration.

Storage backends (evaluated in order)
--------------------------------------
1. Static env-var credentials (USER_CREDENTIALS)
   - Pre-configured accounts, admin console use.
   - Passwords stored as plaintext in the env var — Admin Console concern only.
   - NOT changed in this task.

2. PostgreSQL portal_users table  [PRIMARY — when DATABASE_URL is set]
   - Self-registered User Portal accounts.
   - Passwords stored as bcrypt hashes (passlib CryptContext).
   - Source of truth after init_db.py has been run.

3. Legacy JSON file fallback  [SECONDARY — when DATABASE_URL is NOT set]
   - data/registered_users.json with SHA-256 salted hashes.
   - Preserved for environments that have not yet configured PostgreSQL.
   - Deprecated: will be superseded once DATABASE_URL is configured.

Password hashing
----------------
New registrations always use bcrypt (passlib CryptContext, same configuration
as jwt_utils.py).  The legacy SHA-256 scheme is kept only for the JSON fallback
path and is NOT used for PostgreSQL-backed registrations.

NEEDS_RESET sentinel
--------------------
Users imported from the legacy JSON file by init_db.py have
password_hash = 'NEEDS_RESET'.  verify_login() detects this sentinel and
returns False, causing the login to fail with an appropriate log message.
The user must re-register to obtain a bcrypt-hashed PostgreSQL record.
"""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
from pathlib import Path

import bcrypt as _bcrypt_lib

from app.config import settings

LOGGER = logging.getLogger(__name__)

# Sentinel written by init_db.py for users imported from the legacy JSON file.
_NEEDS_RESET_SENTINEL = "NEEDS_RESET"


# ---------------------------------------------------------------------------
# Internal helpers — bcrypt (using the bcrypt library directly)
# Uses bcrypt.hashpw / bcrypt.checkpw — works correctly with bcrypt 4.x and 5.x.
# Avoids passlib's CryptContext which is incompatible with bcrypt >= 4.0.
# ---------------------------------------------------------------------------


def _bcrypt_hash(plain_password: str) -> str:
    """Return a bcrypt hash of the plain-text password."""
    salt = _bcrypt_lib.gensalt()
    return _bcrypt_lib.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def _bcrypt_verify(plain_password: str, hashed: str) -> bool:
    """Verify a plain-text password against a stored bcrypt hash."""
    try:
        return _bcrypt_lib.checkpw(
            plain_password.encode("utf-8"),
            hashed.encode("utf-8"),
        )
    except Exception as exc:
        LOGGER.warning("bcrypt verification error: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Internal helpers — legacy SHA-256 (JSON fallback only, NOT used for PG)
# ---------------------------------------------------------------------------


def _sha256_hash(password: str, salt: str | None = None) -> str:
    """Hash a password using SHA-256 with a salt. Returns 'salt:hash'."""
    if salt is None:
        salt = secrets.token_hex(8)
    hashed = hashlib.sha256((password + salt).encode("utf-8")).hexdigest()
    return f"{salt}:{hashed}"


def _sha256_verify(plain_password: str, stored_value: str) -> bool:
    """Verify a plain-text password against a stored 'salt:sha256hash' value."""
    if ":" not in stored_value:
        return False
    salt, stored_hash = stored_value.split(":", 1)
    _, computed_hash = _sha256_hash(plain_password, salt).split(":", 1)
    return secrets.compare_digest(
        computed_hash.encode("utf-8"), stored_hash.encode("utf-8")
    )


# ---------------------------------------------------------------------------
# PostgreSQL backend operations
# ---------------------------------------------------------------------------


def _pg_user_exists(username: str) -> bool:
    """Return True if the username already exists in portal_users."""
    from app.db.database import get_connection

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM portal_users WHERE username = %s LIMIT 1",
                (username,),
            )
            exists = cur.fetchone() is not None
            if exists:
                LOGGER.info("AUTH | POSTGRES_USER_FOUND | username=%s", username)
            else:
                LOGGER.info("AUTH | POSTGRES_USER_NOT_FOUND | username=%s", username)
            return exists


def _pg_register_user(username: str, plain_password: str) -> tuple[bool, str]:
    """
    Insert a new user into portal_users with a bcrypt-hashed password.

    Returns (True, success_message) or (False, error_message).
    """
    from app.db.database import DatabaseConnectionError, get_connection

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO portal_users (username, password_hash)
                    VALUES (%s, %s)
                    """,
                    (username, _bcrypt_hash(plain_password)),
                )
        LOGGER.info("AUTH | USER_REGISTRATION_SUCCESS | username=%s", username)
        return True, "Account created successfully!"
    except DatabaseConnectionError as exc:
        LOGGER.error("AUTH | USER_REGISTRATION_FAILED | username=%s | reason=database_unavailable", username)
        return False, f"Registration failed: database unavailable. ({exc})"
    except Exception as exc:
        # Check for unique-constraint violation (psycopg2 IntegrityError)
        err_msg = str(exc).lower()
        if "unique" in err_msg or "duplicate" in err_msg:
            LOGGER.warning("AUTH | USER_REGISTRATION_FAILED | username=%s | reason=username_taken", username)
            return False, f"Username '{username}' is already taken."
        LOGGER.error("AUTH | USER_REGISTRATION_FAILED | username=%s | reason=storage_error", username)
        return False, f"Registration failed due to a storage error: {exc}"


def _pg_verify_login(username: str, plain_password: str) -> bool:
    """
    Look up the user in portal_users and verify the bcrypt password.

    Returns True on success, False on any failure (wrong password, missing
    user, NEEDS_RESET sentinel, or connection error).
    """
    from app.db.database import DatabaseConnectionError, get_connection

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT password_hash FROM portal_users WHERE username = %s",
                    (username,),
                )
                row = cur.fetchone()
    except DatabaseConnectionError as exc:
        LOGGER.error("AUTH | LOGIN_FAILED | username=%s | reason=database_unavailable", username)
        return False
    except Exception as exc:
        LOGGER.error("AUTH | LOGIN_FAILED | username=%s | reason=database_error", username)
        return False

    if row is None:
        LOGGER.warning("AUTH | LOGIN_FAILED | username=%s | reason=user_not_found", username)
        return False

    stored_hash: str = row[0]

    if stored_hash == _NEEDS_RESET_SENTINEL:
        LOGGER.warning("AUTH | LOGIN_FAILED | username=%s | reason=password_reset_required", username)
        return False

    result = _bcrypt_verify(plain_password, stored_hash)
    if result:
        LOGGER.info("AUTH | PASSWORD_VERIFIED | username=%s", username)
    else:
        LOGGER.warning("AUTH | PASSWORD_VERIFICATION_FAILED | username=%s | reason=invalid_password", username)
    return result


# ---------------------------------------------------------------------------
# AuthManager — public interface (unchanged API surface)
# ---------------------------------------------------------------------------


class AuthManager:
    """
    Manages username/password validation for the User Portal and Admin Console.

    Public methods
    --------------
    get_users_dict()    — parse USER_CREDENTIALS env var (Admin Console only)
    verify_login()      — check credentials against all applicable backends
    register_user()     — register a new User Portal account
    """

    @classmethod
    def _registered_users_file(cls) -> Path:
        """Return the legacy JSON registration file path (fallback only)."""
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        return settings.data_dir / "registered_users.json"

    @classmethod
    def get_users_dict(cls) -> dict[str, str]:
        """
        Parse USER_CREDENTIALS env var into a {username: plaintext_password} dict.

        Used exclusively for the Admin Console static accounts.
        NOT used for User Portal PostgreSQL-backed accounts.
        """
        users: dict[str, str] = {}
        raw_creds = settings.user_credentials.strip()
        if raw_creds:
            for item in raw_creds.split(","):
                if not item.strip():
                    continue
                if ":" in item:
                    parts = item.split(":", 1)
                    username = parts[0].strip()
                    password = parts[1].strip()
                    if username and password:
                        users[username] = password
                else:
                    LOGGER.warning("Malformed credential block ignored: '%s'", item)
        return users

    @classmethod
    def user_exists(cls, username: str | None) -> bool:
        """
        Check if a user exists across all configured backends.

        Order:
        1. Static USER_CREDENTIALS env-var accounts.
        2. PostgreSQL portal_users table (when DATABASE_URL is set).
        3. Legacy registered_users.json fallback.

        Returns True if the username exists in any valid store.
        """
        if not username or not username.strip():
            return False

        user_key = username.strip()

        # 1. Static env-var credentials
        if user_key in cls.get_users_dict():
            return True

        # 2. PostgreSQL backend
        if settings.database_url:
            try:
                return _pg_user_exists(user_key)
            except Exception as exc:
                LOGGER.warning("PostgreSQL user_exists check error for '%s': %s", user_key, exc)
                return False

        # 3. Legacy JSON fallback
        reg_file = cls._registered_users_file()
        if reg_file.exists():
            try:
                with open(reg_file, "r", encoding="utf-8") as fh:
                    reg_users: dict = json.load(fh)
                return user_key in reg_users
            except Exception as exc:
                LOGGER.warning("Failed to read legacy registered_users.json: %s", exc)

        return False

    @classmethod
    def verify_login(cls, username: str | None, password: str | None) -> bool:
        """
        Verify username and password against all configured backends.

        Order:
        1. Static USER_CREDENTIALS env-var accounts (Admin Console / pre-configured).
        2. PostgreSQL portal_users table (when DATABASE_URL is set).
        3. Legacy registered_users.json fallback (when DATABASE_URL is NOT set).

        Returns True only when credentials are valid.
        """
        if not username or not password:
            return False

        user_key = username.strip()
        pass_val = password.strip()

        # --- 1. Static env-var credentials (Admin Console accounts) ---
        static_users = cls.get_users_dict()
        if user_key in static_users:
            correct_password = static_users[user_key]
            if secrets.compare_digest(
                correct_password.encode("utf-8"), pass_val.encode("utf-8")
            ):
                LOGGER.info("Static user login succeeded for: %s", user_key)
                return True
            LOGGER.warning("Static user login failed for: %s", user_key)
            return False

        # --- 2. PostgreSQL (User Portal registered accounts) ---
        if settings.database_url:
            return _pg_verify_login(user_key, pass_val)

        # --- 3. Legacy JSON file fallback ---
        reg_file = cls._registered_users_file()
        if reg_file.exists():
            try:
                with open(reg_file, "r", encoding="utf-8") as fh:
                    reg_users: dict = json.load(fh)
                if user_key in reg_users:
                    stored_value = reg_users[user_key]
                    if _sha256_verify(pass_val, stored_value):
                        LOGGER.info(
                            "Legacy JSON user login succeeded for: %s", user_key
                        )
                        return True
            except Exception as exc:
                LOGGER.warning("Failed to read legacy registered_users.json: %s", exc)

        LOGGER.warning("Login verification failed for: %s", user_key)
        return False

    @classmethod
    def register_user(cls, username: str, password: str) -> tuple[bool, str]:
        """
        Register a new User Portal account.

        When DATABASE_URL is configured, the user is written to the
        portal_users PostgreSQL table with a bcrypt-hashed password.

        When DATABASE_URL is NOT configured, the legacy JSON file is used
        with SHA-256 salted hashing (preserved for backward compatibility).

        Returns (True, success_message) or (False, error_message).
        """
        username = username.strip()
        password = password.strip()
        if not username or not password:
            return False, "Username and password cannot be empty."

        # Never allow a portal user to shadow a static admin account.
        static_users = cls.get_users_dict()
        if username in static_users:
            return False, f"Username '{username}' is already taken."

        # --- PostgreSQL backend ---
        if settings.database_url:
            # Check for existing user before attempting insert (gives clearer error)
            try:
                if _pg_user_exists(username):
                    return False, f"Username '{username}' is already taken."
            except Exception:
                pass  # _pg_register_user will handle the constraint violation
            return _pg_register_user(username, password)

        # --- Legacy JSON fallback ---
        reg_file = cls._registered_users_file()
        reg_users: dict = {}
        if reg_file.exists():
            try:
                with open(reg_file, "r", encoding="utf-8") as fh:
                    reg_users = json.load(fh)
            except Exception:
                pass

        if username in reg_users:
            return False, f"Username '{username}' is already taken."

        reg_users[username] = _sha256_hash(password)

        try:
            with open(reg_file, "w", encoding="utf-8") as fh:
                json.dump(reg_users, fh, indent=2, ensure_ascii=False)
            LOGGER.info("Legacy JSON: registered new user '%s'.", username)
            return True, "Account created successfully!"
        except Exception as exc:
            LOGGER.error("Legacy JSON: failed to save user '%s': %s", username, exc)
            return False, f"Registration failed due to storage error: {exc}"
