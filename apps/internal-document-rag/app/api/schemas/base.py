from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ResponseModel(BaseModel, Generic[T]):
    """Standardized API response wrapper."""

    success: bool = True
    message: str = "Request processed successfully"
    data: T | None = None
    errors: list[str] | None = None


class ErrorResponse(BaseModel):
    """Error response model."""

    success: bool = False
    message: str = "An error occurred"
    errors: list[str] = Field(default_factory=list)
