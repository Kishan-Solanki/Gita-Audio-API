"""User profile, favorites, progress, streak, and memory log routes."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.deps import CurrentUser, DBSession, Pagination
from app.schemas.favorites import FavoriteListResponse, FavoriteResponse
from app.schemas.pregnancy import StreakResponse
from app.schemas.progress import (
    ChapterProgressResponse,
    ProgressResponse,
    ProgressUpdateRequest,
    SanskarLogResponse,
)
from app.schemas.user import UserResponse, UserUpdateRequest
from app.services.favorites_service import (
    add_favorite,
    get_favorites,
    remove_favorite,
)
from app.services.progress_service import (
    get_sanskar_log,
    get_user_progress,
    update_progress,
)
from app.services.streak_service import get_streak

router = APIRouter(prefix="/me", tags=["Profile"])


# ── Profile ──────────────────────────────────────────────────────────────


@router.get("", response_model=UserResponse, summary="Get current user profile")
async def get_profile(current_user: CurrentUser) -> UserResponse:
    """Return the profile of the currently authenticated user."""
    return UserResponse.model_validate(current_user)


@router.patch("", response_model=UserResponse, summary="Update user profile")
async def update_profile(
    data: UserUpdateRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> UserResponse:
    """Update profile fields (preferred language, pregnancy start/due date, timezone, etc.)."""
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)

    await db.flush()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user)


# ── Favorites ────────────────────────────────────────────────────────────


@router.get(
    "/favorites",
    response_model=FavoriteListResponse,
    summary="List user's favorited shloks",
)
async def list_favorites(
    current_user: CurrentUser,
    db: DBSession,
    pagination: Pagination,
) -> FavoriteListResponse:
    """Return a paginated list of shloks favorited by the current user."""
    return await get_favorites(
        db,
        user_id=current_user.id,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.put(
    "/favorites/{shlok_id}",
    response_model=FavoriteResponse,
    summary="Add shlok to favorites",
)
async def favorite_shlok(
    shlok_id: int,
    current_user: CurrentUser,
    db: DBSession,
) -> FavoriteResponse:
    """Add a shlok to favorites (idempotent)."""
    return await add_favorite(db, user_id=current_user.id, shlok_id=shlok_id)


@router.delete(
    "/favorites/{shlok_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove shlok from favorites",
)
async def unfavorite_shlok(
    shlok_id: int,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    """Remove a shlok from favorites (idempotent)."""
    await remove_favorite(db, user_id=current_user.id, shlok_id=shlok_id)


# ── Progress & Streak ────────────────────────────────────────────────────


@router.put(
    "/progress/{shlok_id}",
    response_model=ProgressResponse,
    summary="Update playback progress for a shlok",
)
async def record_progress(
    shlok_id: int,
    data: ProgressUpdateRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> ProgressResponse:
    """Record current position and whether listening completed.

    Increments listen_count when completed transitions to True.
    """
    return await update_progress(
        db,
        user_id=current_user.id,
        shlok_id=shlok_id,
        position_sec=data.position_sec,
        completed=data.completed,
    )


@router.get(
    "/progress",
    response_model=list[ChapterProgressResponse],
    summary="Get per-chapter listening progress",
)
async def chapter_progress_summary(
    current_user: CurrentUser,
    db: DBSession,
) -> list[ChapterProgressResponse]:
    """Return a 18-chapter list showing how many shloks were completed vs total verses."""
    return await get_user_progress(db, user_id=current_user.id)


@router.get(
    "/streak",
    response_model=StreakResponse,
    summary="Get user practice streak",
)
async def user_streak(
    current_user: CurrentUser,
    db: DBSession,
) -> StreakResponse:
    """Compute current streak with 1-day grace period, practice days this week, and total completed."""
    return await get_streak(db, user_id=current_user.id)


@router.get(
    "/sanskar-log",
    response_model=SanskarLogResponse,
    summary="Get unified Sanskar memory log",
)
async def sanskar_memory_log(
    current_user: CurrentUser,
    db: DBSession,
    pagination: Pagination,
) -> SanskarLogResponse:
    """Return merged date-ordered list of completed sanskar reflections and favorited shloks."""
    return await get_sanskar_log(
        db,
        user_id=current_user.id,
        limit=pagination.limit,
        offset=pagination.offset,
    )
