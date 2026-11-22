"""Pregnancy timeline endpoints: 40 weeks of Garbh Sanskar themes."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.errors import NotFoundError
from app.db.models import AudioTrack, Chapter, Shlok, WeekShlok, WeekTheme
from app.deps import DBSession
from app.schemas.content import ShlokBrief
from app.schemas.pregnancy import WeekBrief, WeekDetailResponse

router = APIRouter(prefix="/weeks", tags=["Pregnancy"])


@router.get(
    "",
    response_model=list[WeekBrief],
    summary="List all 40 pregnancy weeks",
)
async def list_weeks(db: DBSession) -> list[WeekBrief]:
    """Return all 40 weeks with title and trimester for the pregnancy timeline carousel."""
    result = await db.execute(select(WeekTheme).order_by(WeekTheme.week.asc()))
    weeks = result.scalars().all()
    return [
        WeekBrief(
            week=w.week,
            title_en=w.title_en,
            title_hi=w.title_hi,
            trimester=w.trimester,
        )
        for w in weeks
    ]


@router.get(
    "/{n}",
    response_model=WeekDetailResponse,
    summary="Get details for pregnancy week n",
)
async def get_week(n: int, db: DBSession) -> WeekDetailResponse:
    """Return theme, description, and recommended shloks (with audio status) for week n."""
    stmt = (
        select(WeekTheme)
        .options(
            selectinload(WeekTheme.week_shloks)
            .selectinload(WeekShlok.shlok)
            .selectinload(Shlok.chapter),
            selectinload(WeekTheme.week_shloks)
            .selectinload(WeekShlok.shlok)
            .selectinload(Shlok.audio_tracks),
        )
        .where(WeekTheme.week == n)
    )
    result = await db.execute(stmt)
    week_theme = result.scalar_one_or_none()

    if week_theme is None:
        raise NotFoundError(f"Week {n} not found.")

    recommended: list[ShlokBrief] = []
    sorted_ws = sorted(week_theme.week_shloks, key=lambda ws: ws.day_order)
    for ws in sorted_ws:
        shlok = ws.shlok
        if shlok and shlok.chapter:
            has_audio = any(
                track.is_active and track.kind == "shlok"
                for track in shlok.audio_tracks
            )
            recommended.append(
                ShlokBrief(
                    chapter=shlok.chapter.number,
                    verse=shlok.verse_number,
                    reference=f"{shlok.chapter.number}.{shlok.verse_number}",
                    sanskrit=shlok.sanskrit,
                    transliteration=shlok.transliteration,
                    has_audio=has_audio,
                )
            )

    return WeekDetailResponse(
        week=week_theme.week,
        theme_key=week_theme.theme_key,
        title_en=week_theme.title_en,
        title_hi=week_theme.title_hi,
        description_en=week_theme.description_en,
        description_hi=week_theme.description_hi,
        trimester=week_theme.trimester,
        recommended_shloks=recommended,
    )
