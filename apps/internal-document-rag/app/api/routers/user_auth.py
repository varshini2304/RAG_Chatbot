"""
User Portal Authentication Router
===================================
Provides user-facing registration, login, and identity-verification endpoints.

This router is completely separate from the admin console auth router
(`app/api/routers/auth.py`).  Admin credentials and user credentials are
handled by different code paths and produce incompatible token types.

Endpoints:
    POST /api/v1/user-auth/register  — register a new user account
    POST /api/v1/user-auth/login     — login and receive a JWT
    GET  /api/v1/user-auth/me        — verify token and return identity
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from app.api.schemas.base import ErrorResponse
from app.api.schemas.user_auth import (
    UserLoginRequest,
    UserMeResponse,
    UserRegisterRequest,
    UserTokenResponse,
)
from app.api.user_auth.jwt_utils import create_access_token
from app.api.user_auth.portal_user import get_portal_user
from app.utils.auth import AuthManager

LOGGER = logging.getLogger(__name__)

router = APIRouter(prefix="/user-auth", tags=["User Portal Authentication"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_error(status_code: int, message: str) -> JSONResponse:
    """Return a standardized error JSON response."""
    body = ErrorResponse(success=False, message=message, errors=[message])
    return JSONResponse(status_code=status_code, content=body.model_dump())


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/register",
    response_model=UserTokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description=(
        "Create a local user account with a hashed password. "
        "Returns a JWT access token on success. "
        "Credentials are stored locally using SHA-256 salted hashing."
    ),
)
def register(payload: UserRegisterRequest) -> UserTokenResponse | JSONResponse:
    """Register a new user and return a JWT on success."""
    username = payload.username.strip()
    password = payload.password.strip()
    confirm_password = payload.confirm_password.strip()

    # --- Basic input validation ---
    if not username:
        return _make_error(status.HTTP_400_BAD_REQUEST, "Username cannot be empty.")
    if not password:
        return _make_error(status.HTTP_400_BAD_REQUEST, "Password cannot be empty.")
    if len(password) < 6:
        return _make_error(
            status.HTTP_400_BAD_REQUEST, "Password must be at least 6 characters."
        )
    if password != confirm_password:
        return _make_error(status.HTTP_400_BAD_REQUEST, "Passwords do not match.")

    LOGGER.info("AUTH | REGISTER_ATTEMPT | username=%s", username)

    # --- Delegate to existing AuthManager (preserves all existing logic) ---
    success, message = AuthManager.register_user(username, password)

    if not success:
        # Conflict: username already taken
        if "already taken" in message.lower():
            LOGGER.warning("AUTH | USER_REGISTRATION_FAILED | username=%s | reason=username_taken", username)
            return _make_error(
                status.HTTP_409_CONFLICT,
                message,
            )
        LOGGER.error("AUTH | USER_REGISTRATION_FAILED | username=%s | reason=%s", username, message)
        return _make_error(status.HTTP_500_INTERNAL_SERVER_ERROR, message)

    LOGGER.info("AUTH | USER_REGISTRATION_SUCCESS | username=%s", username)

    token = create_access_token(username=username)
    return UserTokenResponse(
        success=True,
        token=token,
        username=username,
        avatar_letter=username[0].upper(),
        message="Account created successfully!",
    )


@router.post(
    "/login",
    response_model=UserTokenResponse,
    summary="User Portal Sign-In",
    description=(
        "Authenticate with a registered username and password. "
        "Supports both env-var credentials and self-registered accounts. "
        "Returns a JWT access token on success."
    ),
)
def login(payload: UserLoginRequest) -> UserTokenResponse | JSONResponse:
    """Validate user credentials and return a JWT on success."""
    username = payload.username.strip()
    password = payload.password.strip()

    if not username or not password:
        return _make_error(
            status.HTTP_400_BAD_REQUEST, "Username and password are required."
        )

    LOGGER.info("AUTH | LOGIN_ATTEMPT | username=%s", username)

    # --- Delegate to existing AuthManager (handles env-var + registered users) ---
    if not AuthManager.verify_login(username, password):
        LOGGER.warning("AUTH | LOGIN_FAILED | username=%s | reason=invalid_credentials", username)
        return _make_error(
            status.HTTP_401_UNAUTHORIZED, "Invalid credentials. Access denied."
        )

    LOGGER.info("AUTH | LOGIN_SUCCESS | username=%s", username)

    token = create_access_token(username=username)
    return UserTokenResponse(
        success=True,
        token=token,
        username=username,
        avatar_letter=username[0].upper(),
        message="Login successful",
    )


@router.get(
    "/me",
    response_model=UserMeResponse,
    summary="Verify JWT and Return User Identity",
    description=(
        "Validates the Bearer token from the Authorization header. "
        "Returns 200 with identity information if valid. "
        "The username is derived from the JWT — not from any request parameter."
    ),
)
def me(current_user: str = Depends(get_portal_user)) -> UserMeResponse:  # noqa: B008
    """Return the authenticated user's identity, derived from the validated JWT."""
    return UserMeResponse(
        success=True,
        username=current_user,
        avatar_letter=current_user[0].upper(),
        message="Token is valid",
    )
