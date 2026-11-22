"""Password hashing and JWT helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ── Password hashing ────────────────────────────────────────────────────

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain*."""
    return _pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return ``True`` when *plain* matches *hashed*."""
    return _pwd_ctx.verify(plain, hashed)


# ── JWT tokens ───────────────────────────────────────────────────────────

def _create_token(data: dict[str, Any], expires_delta: timedelta) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(UTC) + expires_delta
    to_encode["iat"] = datetime.now(UTC)
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_access_token(
    subject: int | str,
    *,
    extra: dict[str, Any] | None = None,
) -> str:
    """Create a short-lived access token for *subject* (usually ``user.id``)."""
    payload: dict[str, Any] = {"sub": str(subject), "type": "access"}
    if extra:
        payload.update(extra)
    return _create_token(payload, timedelta(minutes=settings.ACCESS_TOKEN_MINUTES))


def create_refresh_token(
    subject: int | str,
    *,
    extra: dict[str, Any] | None = None,
) -> str:
    """Create a long-lived refresh token for *subject*."""
    payload: dict[str, Any] = {"sub": str(subject), "type": "refresh"}
    if extra:
        payload.update(extra)
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_DAYS))


def decode_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT.  Raises ``JWTError`` on failure."""
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError:
        raise
    return payload


__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
]
