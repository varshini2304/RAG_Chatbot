"""
JWT helper utilities for the user-facing portal authentication.

Separate from the admin console authentication mechanism.
Secret, algorithm, and expiry are read from application Settings.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.config import settings

LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# JWT operations
# ---------------------------------------------------------------------------


def create_access_token(
    username: str,
    extra_claims: dict | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a signed JWT access token embedding the username as the subject.

    Args:
        username: The authenticated user's username (used as JWT `sub`).
        extra_claims: Optional additional payload claims.
        expires_delta: Override the default expiry duration.

    Returns:
        A compact, URL-safe JWT string.
    """
    secret = settings.user_jwt_secret
    algorithm = settings.user_jwt_algorithm
    expire_minutes = settings.user_jwt_expire_minutes

    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=expire_minutes)
    )
    payload: dict = {"sub": username, "exp": expire, "type": "user_portal"}
    if extra_claims:
        payload.update(extra_claims)
    token = jwt.encode(payload, secret, algorithm=algorithm)
    LOGGER.info("AUTH | JWT_CREATED | username=%s", username)
    return token


def decode_access_token(token: str) -> dict:
    """
    Decode and validate a JWT access token.

    Args:
        token: The compact JWT string from the Authorization header.

    Returns:
        The decoded payload dictionary.

    Raises:
        JWTError: If the token is invalid, expired, or tampered.
    """
    secret = settings.user_jwt_secret
    algorithm = settings.user_jwt_algorithm
    return jwt.decode(token, secret, algorithms=[algorithm])


def extract_username_from_token(token: str) -> str | None:
    """
    Safely extract the username (subject) from a JWT token.

    Returns:
        The username string, or None if the token is invalid.
    """
    try:
        payload = decode_access_token(token)
        return payload.get("sub")
    except JWTError as exc:
        LOGGER.warning("AUTH | JWT_REJECTED | reason=%s", exc)
        return None
