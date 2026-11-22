"""Daily Sanskar service: deterministic daily shlok selection and idempotent completion."""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import NotFoundError, ValidationError
from app.db.models import (
    AudioTrack,
    Chapter,
    Shlok,
    ShlokContent,
    SanskarCompletion,
    User,
    WeekShlok,
    WeekTheme,
)
from app.schemas.content import AudioTrackResponse, ShlokContentResponse, ShlokDetailResponse
from app.schemas.pregnancy import DailySanskarResponse, SanskarCompleteResponse, StreakResponse
from app.services.audio_url_service import build_audio_url
from app.services.streak_service import get_streak


# ---------------------------------------------------------------------------
# Week calculation
# ---------------------------------------------------------------------------


def _current_week(user: User, today: date) -> int | None:
    """Derive the user's current pregnancy week (1-40).

    Priority:
      1. ``due_date``: week = 40 − ceil(days_until_due / 7), clamped 1-40.
      2. ``pregnancy_start_date``: week = floor(days_since_start / 7) + 1, clamped 1-40.
      3. Neither date set → ``None`` (needs onboarding).
    """
    if user.due_date is not None:
        days_until_due = (user.due_date - today).days
        if days_until_due < 0:
            return 40  # past due
        week = 40 - math.ceil(days_until_due / 7)
        return max(1, min(week, 40))

    if user.pregnancy_start_date is not None:
        days_since = (today - user.pregnancy_start_date).days
        if days_since < 0:
            return 1  # future start date — treat as week 1
        week = (days_since // 7) + 1
        return max(1, min(week, 40))

    return None


def _user_today(user: User) -> date:
    """Return today's date in the user's timezone."""
    try:
        tz = timezone(timedelta(hours=_tz_offset_hours(user.timezone)))
    except Exception:
        tz = timezone(timedelta(hours=5, minutes=30))  # default IST
    return datetime.now(tz).date()


def _tz_offset_hours(iana_tz: str) -> float:
    """Best-effort IANA timezone → UTC offset in hours.

    For production, prefer ``zoneinfo.ZoneInfo``.  This fallback handles
    ``Asia/Kolkata`` and UTC only; callers should install ``tzdata`` for
    full support.
    """
    try:
        from zoneinfo import ZoneInfo
        dt = datetime.now(ZoneInfo(iana_tz))
        return dt.utcoffset().total_seconds() / 3600  # type: ignore[union-attr]
    except Exception:
        # Hard-coded fallback for the most common timezone
        _KNOWN: dict[str, float] = {
            "Asia/Kolkata": 5.5,
            "UTC": 0.0,
        }
        return _KNOWN.get(iana_tz, 5.5)


# ---------------------------------------------------------------------------
# Daily shlok selection
# ---------------------------------------------------------------------------


async def _select_daily_shlok(
    db: AsyncSession,
    week: int,
    today: date,
) -> Shlok | None:
    """Deterministically pick today's shlok for the given pregnancy week.

    Algorithm:
      1. Load ``WeekShlok`` rows for *week*, ordered by ``day_order``.
      2. ``day_order = (days_since_week_began % shlok_count) + 1``
         (cycling when fewer than 7 shloks are mapped).
      3. If no mappings exist, fall back to the week theme's
         ``recommended_chapter`` and pick a rotating shlok.
      4. Final fallback: first shlok in chapter 1.

    Same user + same day = same shlok (deterministic via ``day_order``).
    """
    # 1. Try direct week → shlok mapping
    stmt = (
        select(WeekShlok)
        .options(
            selectinload(WeekShlok.shlok)
            .selectinload(Shlok.contents),
            selectinload(WeekShlok.shlok)
            .selectinload(Shlok.audio_tracks)
            .selectinload(AudioTrack.reciter),
        )
        .where(WeekShlok.week == week)
        .order_by(WeekShlok.day_order.asc())
    )
    result = await db.execute(stmt)
    week_shloks = result.scalars().all()

    if week_shloks:
        # Calculate how many days into the week we are
        # week_start = today minus (today.weekday()) → Monday-based for consistency
        # But the spec says "days since week began" in the pregnancy sense.
        # We use day_of_year mod count so each day gets a stable shlok.
        count = len(week_shloks)
        day_index = today.toordinal() % count  # stable per calendar day
        return week_shloks[day_index].shlok

    # 2. Fallback: recommended chapter for this week
    theme = await db.scalar(
        select(WeekTheme)
        .options(selectinload(WeekTheme.recommended_chapter))
        .where(WeekTheme.week == week)
    )
    if theme and theme.recommended_chapter:
        return await _rotating_shlok_from_chapter(db, theme.recommended_chapter.id, today)

    # 3. Final fallback: chapter 1
    chapter1 = await db.scalar(
        select(Chapter).where(Chapter.number == 1)
    )
    if chapter1:
        return await _rotating_shlok_from_chapter(db, chapter1.id, today)

    return None


async def _rotating_shlok_from_chapter(
    db: AsyncSession,
    chapter_id: int,
    today: date,
) -> Shlok | None:
    """Pick a rotating shlok from a chapter based on today's date."""
    stmt = (
        select(Shlok)
        .options(
            selectinload(Shlok.contents),
            selectinload(Shlok.audio_tracks).selectinload(AudioTrack.reciter),
        )
        .where(Shlok.chapter_id == chapter_id)
        .order_by(Shlok.verse_number.asc())
    )
    result = await db.execute(stmt)
    shloks = result.scalars().all()
    if not shloks:
        return None
    idx = today.toordinal() % len(shloks)
    return shloks[idx]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def get_daily_sanskar(
    db: AsyncSession,
    user: User,
) -> DailySanskarResponse:
    """Return today's daily sanskar shlok for the user.

    Includes the shlok detail, reflection/bonding prompts, completion status,
    and streak statistics.
    """
    today = _user_today(user)
    week = _current_week(user, today)
    needs_pregnancy_date = week is None

    # Default to week 1 if no pregnancy date set
    effective_week = week or 1

    shlok = await _select_daily_shlok(db, effective_week, today)
    if shlok is None:
        raise NotFoundError("No shlok available for today. Please check content data.")

    # Build shlok detail
    chapter = await db.get(Chapter, shlok.chapter_id)
    chapter_num = chapter.number if chapter else 0

    # Content for user's preferred language
    lang = user.preferred_lang or "en"
    content_resp: ShlokContentResponse | None = None
    reflection_prompt: str | None = None
    bonding_practice: str | None = None

    for c in shlok.contents:
        if c.lang == lang:
            content_resp = ShlokContentResponse(
                lang=c.lang,
                literal_meaning=c.literal_meaning,
                simple_explanation=c.simple_explanation,
                reflection_prompt=c.reflection_prompt,
                bonding_practice=c.bonding_practice,
            )
            reflection_prompt = c.reflection_prompt
            bonding_practice = c.bonding_practice
            break

    # Audio
    audio_resp: AudioTrackResponse | None = None
    for t in shlok.audio_tracks:
        if t.is_active:
            audio_resp = AudioTrackResponse(
                track_id=t.id,
                title=t.title,
                subtitle=t.subtitle,
                language=t.reciter.language,
                url=build_audio_url(t.path),
                duration_sec=t.duration_sec,
                size_bytes=t.size_bytes,
                version=t.version,
                peaks=t.peaks,
            )
            break

    shlok_detail = ShlokDetailResponse(
        chapter=chapter_num,
        verse=shlok.verse_number,
        reference=f"{chapter_num}.{shlok.verse_number}",
        sanskrit=shlok.sanskrit,
        transliteration=shlok.transliteration,
        content=content_resp,
        audio=audio_resp,
        is_favorite=None,
        progress=None,
    )

    # Completion check
    completed_today = await db.scalar(
        select(SanskarCompletion.id).where(
            SanskarCompletion.user_id == user.id,
            SanskarCompletion.date == today,
        )
    ) is not None

    # Streak
    streak = await get_streak(db, user.id)

    return DailySanskarResponse(
        shlok=shlok_detail,
        reflection_prompt=reflection_prompt,
        bonding_practice=bonding_practice,
        completed_today=completed_today,
        streak=streak,
        needs_pregnancy_date=needs_pregnancy_date,
    )


async def complete_sanskar(
    db: AsyncSession,
    user_id: int,
    shlok_id: int,
    reflection_note: str | None = None,
) -> SanskarCompleteResponse:
    """Record a daily sanskar completion (idempotent).

    If the user has already completed today's sanskar, the existing record
    is returned unchanged.

    Args:
        db: Async database session.
        user_id: Authenticated user's ID.
        shlok_id: ID of the shlok being completed.
        reflection_note: Optional personal reflection text.

    Raises:
        NotFoundError: If the shlok does not exist.
    """
    # Verify the shlok exists
    shlok = await db.get(Shlok, shlok_id)
    if shlok is None:
        raise NotFoundError(f"Shlok {shlok_id} not found.")

    # Determine today in the user's timezone
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found.")

    today = _user_today(user)

    # Idempotent: check if already completed today
    existing = await db.scalar(
        select(SanskarCompletion).where(
            SanskarCompletion.user_id == user_id,
            SanskarCompletion.date == today,
        )
    )
    if existing is not None:
        return SanskarCompleteResponse(
            id=existing.id,
            date=existing.date,
            shlok_id=existing.shlok_id,
            reflection_note=existing.reflection_note,
        )

    completion = SanskarCompletion(
        user_id=user_id,
        date=today,
        shlok_id=shlok_id,
        reflection_note=reflection_note,
    )
    db.add(completion)
    await db.flush()

    return SanskarCompleteResponse(
        id=completion.id,
        date=completion.date,
        shlok_id=completion.shlok_id,
        reflection_note=completion.reflection_note,
    )
