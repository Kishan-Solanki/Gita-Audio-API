"""Daily Sanskar endpoints: today's shlok and completion."""

from __future__ import annotations

from fastapi import APIRouter

from app.deps import CurrentUser, DBSession
from app.schemas.pregnancy import (
    DailySanskarResponse,
    SanskarCompleteRequest,
    SanskarCompleteResponse,
)
from app.services.daily_sanskar_service import complete_sanskar, get_daily_sanskar

router = APIRouter(tags=["Daily Sanskar"])


@router.get(
    "/daily-sanskar",
    response_model=DailySanskarResponse,
    summary="Get today's daily sanskar",
)
async def daily_sanskar(
    current_user: CurrentUser,
    db: DBSession,
) -> DailySanskarResponse:
    """Return today's recommended shlok for the user's current pregnancy week.

    Includes full shlok details, maternal reflection prompt, bonding practice,
    whether already completed today, and streak statistics.
    Falls back to a rotating default if no pregnancy start/due date is set.
    """
    return await get_daily_sanskar(db, user=current_user)


@router.post(
    "/sanskar/complete",
    response_model=SanskarCompleteResponse,
    summary="Mark today's sanskar as completed",
)
async def complete_today_sanskar(
    data: SanskarCompleteRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> SanskarCompleteResponse:
    """Record completion of today's sanskar with an optional reflection note.

    Idempotent per local date: subsequent calls on the same day update the note
    and return the existing completion record.
    """
    return await complete_sanskar(
        db,
        user_id=current_user.id,
        shlok_id=data.shlok_id,
        reflection_note=data.reflection_note,
    )
