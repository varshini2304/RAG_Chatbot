from __future__ import annotations

from pydantic import BaseModel


class UserProfileSchema(BaseModel):
    id: str
    username: str
    email: str | None = None
    role: str
    avatar_letter: str
    created_at: str
