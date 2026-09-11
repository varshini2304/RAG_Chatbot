from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.api.dependencies.auth import get_current_user
from app.api.schemas.base import ResponseModel
from app.api.schemas.users import UserProfileSchema
from app.api.services.user_service import UserService

router = APIRouter(tags=["Users & Roles"])


def get_user_service() -> UserService:
    return UserService()


@router.get("/users/me", response_model=ResponseModel[UserProfileSchema])
def get_user_profile(
    current_user: UserProfileSchema = Depends(get_current_user),  # noqa: B008
) -> ResponseModel[UserProfileSchema]:
    """Retrieve authenticated user profile."""
    return ResponseModel(
        success=True,
        message="User profile retrieved successfully",
        data=current_user,
    )


@router.get("/users", response_model=ResponseModel[list[dict[str, Any]]])
def get_users_list(
    service: UserService = Depends(get_user_service),  # noqa: B008
) -> ResponseModel[list[dict[str, Any]]]:
    """Retrieve list of system users."""
    data = service.get_users_list()
    return ResponseModel(
        success=True,
        message="Users list retrieved successfully",
        data=data,
    )


@router.get("/roles", response_model=ResponseModel[list[dict[str, Any]]])
def get_roles_list(
    service: UserService = Depends(get_user_service),  # noqa: B008
) -> ResponseModel[list[dict[str, Any]]]:
    """Retrieve list of user roles and permissions."""
    data = service.get_roles_list()
    return ResponseModel(
        success=True,
        message="Roles list retrieved successfully",
        data=data,
    )


@router.get("/apikeys", response_model=ResponseModel[list[dict[str, Any]]])
def get_api_keys(
    service: UserService = Depends(get_user_service),  # noqa: B008
) -> ResponseModel[list[dict[str, Any]]]:
    """Retrieve list of API key entries."""
    data = service.get_api_keys()
    return ResponseModel(
        success=True,
        message="API keys retrieved successfully",
        data=data,
    )
