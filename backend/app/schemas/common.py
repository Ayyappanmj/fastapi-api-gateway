"""
Common response schemas shared across routers.

Using a consistent envelope (success/message/data or success/error) makes
the frontend's Axios layer simpler: one response shape to parse everywhere.
"""
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = "OK"
    data: T | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: str | None = None


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    page: int
    page_size: int
    total: int
    items: list[T]
