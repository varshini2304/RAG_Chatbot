"""Pydantic request/response schemas for user-portal authentication endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class UserRegisterRequest(BaseModel):
    """Payload for POST /api/v1/user-auth/register."""

    username: str = Field(..., min_length=1, max_length=64, description="Desired username")
    password: str = Field(..., min_length=6, description="Desired password (min 6 chars)")
    confirm_password: str = Field(..., description="Must match password")


class UserLoginRequest(BaseModel):
    """Payload for POST /api/v1/user-auth/login."""

    username: str = Field(..., min_length=1, description="Registered username")
    password: str = Field(..., min_length=1, description="Account password")


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class UserTokenResponse(BaseModel):
    """Returned on successful registration or login."""

    success: bool = True
    token: str = Field(..., description="JWT Bearer token")
    token_type: str = "bearer"
    username: str
    avatar_letter: str
    message: str = "Authentication successful"


class UserMeResponse(BaseModel):
    """Returned by GET /api/v1/user-auth/me."""

    success: bool = True
    username: str
    avatar_letter: str
    message: str = "Token is valid"
