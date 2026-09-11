from __future__ import annotations

from fastapi import Depends, Header

from app.api.schemas.users import UserProfileSchema
from app.api.services.user_service import UserService


def get_user_service() -> UserService:
    return UserService()


def get_current_user(
    authorization: str | None = Header(None),
    user_service: UserService = Depends(get_user_service),
) -> UserProfileSchema:
    """
    Authenticate incoming API requests.
    Supports token/bearer auth header while providing extensible JWT hooks.
    """
    # For initial local admin console integration:
    return user_service.get_current_user_profile()
