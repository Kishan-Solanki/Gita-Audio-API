"""Custom exception hierarchy and FastAPI exception handlers."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
import structlog

logger = structlog.stdlib.get_logger(__name__)


# ── Exception classes ────────────────────────────────────────────────────


class AppError(Exception):
    """Base application error."""

    status_code: int = HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None, **kwargs: Any) -> None:
        self.message = message or self.__class__.message
        self.extra = kwargs
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = HTTP_404_NOT_FOUND
    code = "NOT_FOUND"
    message = "The requested resource was not found."


class UnauthorizedError(AppError):
    status_code = HTTP_401_UNAUTHORIZED
    code = "UNAUTHORIZED"
    message = "Authentication is required."


class ForbiddenError(AppError):
    status_code = HTTP_403_FORBIDDEN
    code = "FORBIDDEN"
    message = "You do not have permission to perform this action."


class ValidationError(AppError):
    status_code = HTTP_400_BAD_REQUEST
    code = "VALIDATION_ERROR"
    message = "The request data is invalid."


class ConflictError(AppError):
    status_code = HTTP_409_CONFLICT
    code = "CONFLICT"
    message = "The request conflicts with the current state of the resource."


# ── Envelope helper ──────────────────────────────────────────────────────


def _error_envelope(code: str, message: str) -> dict[str, Any]:
    return {"error": {"code": code, "message": message}}


# ── Handlers ─────────────────────────────────────────────────────────────


async def _app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    logger.warning(
        "app_error",
        code=exc.code,
        message=exc.message,
        status=exc.status_code,
        **exc.extra,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_envelope(exc.code, exc.message),
    )


async def _validation_error_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    details = "; ".join(
        f"{' -> '.join(str(loc) for loc in e['loc'])}: {e['msg']}"
        for e in exc.errors()
    )
    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
        content=_error_envelope("VALIDATION_ERROR", details),
    )


async def _generic_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception", error=str(exc))
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_envelope("INTERNAL_ERROR", "An unexpected error occurred."),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all custom exception handlers to the FastAPI *app*."""
    app.add_exception_handler(AppError, _app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _generic_error_handler)  # type: ignore[arg-type]


__all__ = [
    "AppError",
    "NotFoundError",
    "UnauthorizedError",
    "ForbiddenError",
    "ValidationError",
    "ConflictError",
    "register_exception_handlers",
]
