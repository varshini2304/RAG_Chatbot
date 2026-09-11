"""
User-portal FastAPI dependency: extract and validate the authenticated user
from the JWT Bearer token.

This dependency is completely independent of the admin console authentication.
The username is ALWAYS derived from the validated JWT — never from request
parameters or headers supplied by the client.
"""

from __future__ import annotations

import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.api.user_auth.jwt_utils import decode_access_token

LOGGER = logging.getLogger(__name__)

# HTTPBearer scheme — extracts the token from "Authorization: Bearer <token>"
_bearer_scheme = HTTPBearer(auto_error=True)


def get_portal_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> str:
    """
    FastAPI dependency that validates the JWT Bearer token and returns the
    authenticated username.

    The username is extracted from the `sub` claim of the validated JWT.
    It is NEVER taken from query parameters or request body.

    Raises:
        HTTPException 401: If the token is missing, invalid, expired, or
                           does not carry a valid user-portal `type` claim.

    Returns:
        The authenticated username string (str), derived from JWT `sub`.
    """
    _unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError as exc:
        LOGGER.warning("AUTH | JWT_REJECTED | reason=%s", exc)
        raise _unauthorized from exc

    # Enforce that the token was issued by the user portal (not admin console)
    if payload.get("type") != "user_portal":
        LOGGER.warning("AUTH | JWT_REJECTED | reason=wrong_token_type | expected=user_portal | got=%s", payload.get("type"))
        raise _unauthorized

    username: str | None = payload.get("sub")
    if not username or not isinstance(username, str) or not username.strip():
        LOGGER.warning("AUTH | JWT_REJECTED | reason=missing_sub_claim")
        raise _unauthorized

    clean_username = username.strip()

    # Enforce that the user still exists in the database / user store
    from app.utils.auth import AuthManager

    if not AuthManager.user_exists(clean_username):
        LOGGER.warning("AUTH | PROTECTED_ACCESS_REJECTED | username=%s | reason=user_not_found", clean_username)
        raise _unauthorized

    LOGGER.info("AUTH | JWT_VALIDATED | username=%s", clean_username)
    return clean_username
