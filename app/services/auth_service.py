"""Authentication service: registration, login, token rotation, and revocation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import ConflictError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.models import RefreshToken, User
from app.schemas.auth import TokenResponse


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _create_tokens(
    db: AsyncSession,
    user: User,
) -> TokenResponse:
    """Create an access + refresh token pair and persist the refresh hash.

    Returns a ``TokenResponse`` ready for the client.
    """
    access_token = create_access_token(user.id)
    raw_refresh = create_refresh_token(user.id)
    refresh_hash = hash_password(raw_refresh)

    expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_DAYS)

    db_token = RefreshToken(
        user_id=user.id,
        token_hash=refresh_hash,
        expires_at=expires_at,
    )
    db.add(db_token)
    await db.flush()

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        token_type="bearer",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def register_user(
    db: AsyncSession,
    email: str,
    password: str,
    display_name: str,
) -> TokenResponse:
    """Register a new user and return a fresh token pair.

    Raises:
        ConflictError: If a user with *email* already exists.
    """
    existing = await db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise ConflictError("A user with this email already exists.")

    user = User(
        email=email,
        password_hash=hash_password(password),
        display_name=display_name,
    )
    db.add(user)
    await db.flush()  # populate user.id

    tokens = await _create_tokens(db, user)
    return tokens


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> TokenResponse:
    """Verify credentials and return a fresh token pair.

    Raises:
        UnauthorizedError: If the email is not found or the password is wrong.
    """
    user = await db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(password, user.password_hash):
        raise UnauthorizedError("Invalid email or password.")

    if not user.is_active:
        raise UnauthorizedError("This account has been deactivated.")

    tokens = await _create_tokens(db, user)
    return tokens


async def refresh_tokens(
    db: AsyncSession,
    refresh_token: str,
) -> TokenResponse:
    """Rotate a refresh token and return a new access + refresh pair.

    The old refresh token is revoked on success (token rotation).

    Raises:
        UnauthorizedError: If the token is invalid, expired, or already revoked.
    """
    # 1. Decode the JWT
    try:
        payload = decode_token(refresh_token)
    except JWTError:
        raise UnauthorizedError("Invalid or expired refresh token.")

    if payload.get("type") != "refresh":
        raise UnauthorizedError("Token is not a refresh token.")

    user_id = int(payload["sub"])

    # 2. Find a matching, non-revoked token for this user
    stmt = (
        select(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
        .order_by(RefreshToken.id.desc())
    )
    result = await db.execute(stmt)
    db_tokens = result.scalars().all()

    matched_token: RefreshToken | None = None
    for db_tok in db_tokens:
        if verify_password(refresh_token, db_tok.token_hash):
            matched_token = db_tok
            break

    if matched_token is None:
        raise UnauthorizedError("Refresh token not recognised or already revoked.")

    if matched_token.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        raise UnauthorizedError("Refresh token has expired.")

    # 3. Revoke the old token
    matched_token.revoked_at = datetime.now(UTC)  # type: ignore[assignment]
    await db.flush()

    # 4. Issue fresh pair
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("User account not found or deactivated.")

    return await _create_tokens(db, user)


async def revoke_refresh_token(
    db: AsyncSession,
    user_id: int,
    refresh_token: str,
) -> None:
    """Revoke a specific refresh token for a user (logout).

    This is idempotent: revoking an already-revoked token is a no-op.

    Raises:
        UnauthorizedError: If the token doesn't match any stored hash for the user.
    """
    stmt = (
        select(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    db_tokens = result.scalars().all()

    for db_tok in db_tokens:
        if verify_password(refresh_token, db_tok.token_hash):
            db_tok.revoked_at = datetime.now(UTC)  # type: ignore[assignment]
            await db.flush()
            return

    # If we get here, no matching active token was found — that's acceptable
    # for idempotent logout, but we raise so callers know.
    raise UnauthorizedError("Refresh token not recognised or already revoked.")
