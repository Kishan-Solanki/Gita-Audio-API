"""Shlok screen endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.deps import DBSession, OptionalUser
from app.schemas.content import ShlokDetailResponse
from app.services.content_service import get_shlok_detail

router = APIRouter(tags=["Shloks"])


@router.get(
    "/shloks/{chapter}/{verse}",
    response_model=ShlokDetailResponse,
    summary="Get detailed shlok view",
)
async def get_shlok(
    chapter: int,
    verse: int,
    db: DBSession,
    optional_user: OptionalUser,
    lang: str = Query("en", description="Language code ('en' or 'hi')"),
    audio_language: str | None = Query(None, description="Optional audio language code"),
) -> ShlokDetailResponse:
    """Return full shlok screen payload: Devanagari text, transliteration,

    literal meaning, maternal explanation, reflection prompt, bonding practice,
    and audio track details (or null if not yet uploaded).
    Includes is_favorite and progress when authenticated.
    """
    user_id = optional_user.id if optional_user else None
    return await get_shlok_detail(
        db,
        chapter_num=chapter,
        verse_num=verse,
        lang=lang,
        user_id=user_id,
        audio_language=audio_language,
    )
