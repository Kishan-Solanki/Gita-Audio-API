"""Shared FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.db.models.user import User
from app.db.session import get_db

# ── Database dependency (re-export for convenience) ──────────────────────

DBSession = Annotated[AsyncSession, Depends(get_db)]

# ── Auth helpers ─────────────────────────────────────────────────────────

_bearer_scheme = HTTPBearer(auto_error=False)


async def _resolve_user(
    token: str,
    db: AsyncSession,
) -> User:
    """Decode *token*, look up the user, and return it or raise."""
    try:
        payload = decode_token(token)
    except JWTError:
        raise UnauthorizedError("Invalid or expired token.")

    if payload.get("type") != "access":
        raise UnauthorizedError("Token type is not 'access'.")

    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise UnauthorizedError("Token has no subject.")

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise UnauthorizedError("Invalid token subject.")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise UnauthorizedError("User not found.")
    if not user.is_active:
        raise UnauthorizedError("User account is deactivated.")

    return user


async def get_current_user(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(_bearer_scheme)
    ],
    db: DBSession,
) -> User:
    """Require a valid access token and return the authenticated ``User``."""
    if credentials is None:
        raise UnauthorizedError("Missing authorization header.")
    return await _resolve_user(credentials.credentials, db)


async def get_current_admin_user(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Like ``get_current_user`` but also enforces ``is_admin``."""
    if not user.is_admin:
        raise ForbiddenError("Admin privileges required.")
    return user


async def get_optional_user(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(_bearer_scheme)
    ],
    db: DBSession,
) -> User | None:
    """Return the authenticated user if a valid token is supplied, else ``None``."""
    if credentials is None:
        return None
    try:
        return await _resolve_user(credentials.credentials, db)
    except UnauthorizedError:
        return None


# ── Pagination ───────────────────────────────────────────────────────────


class PaginationParams:
    """Inject as a dependency to get validated ``limit`` / ``offset`` params."""

    def __init__(
        self,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> None:
        self.limit = limit
        self.offset = offset


# ── Type aliases for route signatures ────────────────────────────────────

CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(get_current_admin_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
Pagination = Annotated[PaginationParams, Depends()]

__all__ = [
    "DBSession",
    "CurrentUser",
    "AdminUser",
    "OptionalUser",
    "Pagination",
    "PaginationParams",
    "get_current_user",
    "get_current_admin_user",
    "get_optional_user",
    "get_db",
]
