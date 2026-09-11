"""Authentication request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    token: str
    username: str
    role: str
    avatar_letter: str
    message: str = "Login successful"
