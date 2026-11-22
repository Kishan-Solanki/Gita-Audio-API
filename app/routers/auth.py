"""Authentication routes: register, login, refresh, and logout."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.deps import CurrentUser, DBSession
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.services.auth_service import (
    authenticate_user,
    refresh_tokens,
    register_user,
    revoke_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    data: RegisterRequest,
    db: DBSession,
) -> TokenResponse:
    """Register a new user account and return an access/refresh token pair."""
    return await register_user(
        db,
        email=data.email,
        password=data.password,
        display_name=data.display_name,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login",
)
async def login(
    data: LoginRequest,
    db: DBSession,
) -> TokenResponse:
    """Authenticate with email and password and return access/refresh tokens."""
    return await authenticate_user(
        db,
        email=data.email,
        password=data.password,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
)
async def refresh(
    data: RefreshRequest,
    db: DBSession,
) -> TokenResponse:
    """Rotate the refresh token and return a new access/refresh token pair."""
    return await refresh_tokens(db, refresh_token=data.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="User logout",
)
async def logout(
    data: RefreshRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    """Revoke the given refresh token for the authenticated user."""
    await revoke_refresh_token(
        db, user_id=current_user.id, refresh_token=data.refresh_token
    )
