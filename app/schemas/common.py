"""Common response schemas used across the Garbh Journey Gita Audio API."""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Structured error detail returned inside every error response."""

    model_config = ConfigDict(from_attributes=True)

    code: str = Field(..., description="Machine-readable error code, e.g. 'AUTH_INVALID_CREDENTIALS'.")
    message: str = Field(..., description="Human-readable error message.")


class ErrorResponse(BaseModel):
    """Standard envelope for all API error responses."""

    model_config = ConfigDict(from_attributes=True)

    error: ErrorDetail


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper.

    Subclass or instantiate with a concrete type for ``items``.
    """

    model_config = ConfigDict(from_attributes=True)

    items: list[T] = Field(default_factory=list, description="Page of results.")
    total: int = Field(..., ge=0, description="Total number of matching records.")
    limit: int = Field(..., ge=1, description="Maximum items per page.")
    offset: int = Field(..., ge=0, description="Zero-based offset of the first item in this page.")


class HealthResponse(BaseModel):
    """Liveness probe response."""

    model_config = ConfigDict(from_attributes=True)

    status: str = Field(..., examples=["ok"], description="Service status.")
    version: str = Field(..., examples=["1.0.0"], description="API version string.")


class HealthReadyResponse(BaseModel):
    """Readiness probe response — includes dependency checks."""

    model_config = ConfigDict(from_attributes=True)

    status: str = Field(..., examples=["ok"], description="Overall readiness status.")
    database: str = Field(..., examples=["connected"], description="Database connectivity status.")
    version: str = Field(..., examples=["1.0.0"], description="API version string.")
