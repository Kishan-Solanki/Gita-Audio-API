"""Content service: chapters, shloks, topics, reciters, and featured chapters."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import NotFoundError
from app.db.models import (
    AudioTrack,
    Chapter,
    ChapterTopic,
    Favorite,
    ListenProgress,
    Reciter,
    Shlok,
    ShlokContent,
    Topic,
    WeekTheme,
)
from app.schemas.content import (
    AudioTrackResponse,
    ChapterListResponse,
    ChapterProgressBrief,
    ChapterResponse,
    FeaturedChapterResponse,
    ReciterResponse,
    ShlokBrief,
    ShlokContentResponse,
    ShlokDetailResponse,
    TopicResponse,
)
from app.schemas.progress import ProgressResponse
from app.services.audio_url_service import build_audio_url


# ---------------------------------------------------------------------------
# Chapters
# ---------------------------------------------------------------------------


async def get_chapters(
    db: AsyncSession,
    *,
    topic_slug: str | None = None,
    user_id: int | None = None,
    lang: str = "en",
) -> ChapterListResponse:
    """Return all chapters, optionally filtered by topic.

    If *user_id* is provided, each chapter includes per-user progress.

    Args:
        db: Async database session.
        topic_slug: When given, only return chapters tagged with this topic.
        user_id: Authenticated user's ID for progress enrichment.
        lang: Language code (unused at chapter level but kept for API consistency).

    Returns:
        ``ChapterListResponse`` with chapters and total count.
    """
    stmt = (
        select(Chapter)
        .options(
            selectinload(Chapter.topics).selectinload(ChapterTopic.topic),
        )
        .order_by(Chapter.sort_order.asc(), Chapter.number.asc())
    )

    if topic_slug:
        stmt = stmt.join(Chapter.topics).join(ChapterTopic.topic).where(
            Topic.slug == topic_slug,
        )

    result = await db.execute(stmt)
    chapters = result.scalars().unique().all()

    # Pre-fetch user progress when authenticated
    progress_map: dict[int, ChapterProgressBrief] = {}
    if user_id is not None:
        progress_map = await _build_chapter_progress_map(db, user_id)

    chapter_responses = [
        _chapter_to_response(ch, progress_map.get(ch.id))
        for ch in chapters
    ]

    return ChapterListResponse(
        chapters=chapter_responses,
        total=len(chapter_responses),
    )


async def get_chapter(
    db: AsyncSession,
    chapter_number: int,
    lang: str = "en",
) -> ChapterResponse:
    """Return detailed information for a single chapter.

    Raises:
        NotFoundError: If no chapter with *chapter_number* exists.
    """
    stmt = (
        select(Chapter)
        .options(
            selectinload(Chapter.topics).selectinload(ChapterTopic.topic),
        )
        .where(Chapter.number == chapter_number)
    )
    chapter = await db.scalar(stmt)
    if chapter is None:
        raise NotFoundError(f"Chapter {chapter_number} not found.")

    return _chapter_to_response(chapter)


async def get_chapter_shloks(
    db: AsyncSession,
    chapter_number: int,
    limit: int = 20,
    offset: int = 0,
    lang: str = "en",
) -> dict:
    """Return paginated shlok briefs for a chapter.

    Returns:
        A dict with ``shloks`` (list of ``ShlokBrief``) and ``total`` count.

    Raises:
        NotFoundError: If the chapter does not exist.
    """
    chapter = await db.scalar(
        select(Chapter).where(Chapter.number == chapter_number)
    )
    if chapter is None:
        raise NotFoundError(f"Chapter {chapter_number} not found.")

    total = await db.scalar(
        select(func.count(Shlok.id)).where(Shlok.chapter_id == chapter.id)
    )

    stmt = (
        select(Shlok)
        .options(selectinload(Shlok.audio_tracks))
        .where(Shlok.chapter_id == chapter.id)
        .order_by(Shlok.verse_number.asc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    shloks = result.scalars().all()

    return {
        "shloks": [_shlok_to_brief(s, chapter_number) for s in shloks],
        "total": total or 0,
    }


async def get_shlok_detail(
    db: AsyncSession,
    chapter_num: int,
    verse_num: int,
    lang: str = "en",
    user_id: int | None = None,
    audio_language: str | None = None,
) -> ShlokDetailResponse:
    """Return full detail for a single shlok including content, audio, and user state.

    Args:
        db: Async database session.
        chapter_num: Chapter number.
        verse_num: Verse number within the chapter.
        lang: Desired language for content fields.
        user_id: Authenticated user's ID for favorites/progress enrichment.

    Raises:
        NotFoundError: If the chapter or verse does not exist.
    """
    chapter = await db.scalar(
        select(Chapter).where(Chapter.number == chapter_num)
    )
    if chapter is None:
        raise NotFoundError(f"Chapter {chapter_num} not found.")

    stmt = (
        select(Shlok)
        .options(
            selectinload(Shlok.contents),
            selectinload(Shlok.audio_tracks).selectinload(AudioTrack.reciter),
        )
        .where(Shlok.chapter_id == chapter.id, Shlok.verse_number == verse_num)
    )
    shlok = await db.scalar(stmt)
    if shlok is None:
        raise NotFoundError(f"Verse {chapter_num}.{verse_num} not found.")

    # Pick the content for the requested language
    content: ShlokContentResponse | None = None
    for c in shlok.contents:
        if c.lang == lang:
            content = ShlokContentResponse(
                lang=c.lang,
                literal_meaning=c.literal_meaning,
                simple_explanation=c.simple_explanation,
                reflection_prompt=c.reflection_prompt,
                bonding_practice=c.bonding_practice,
            )
            break

    # Prefer the requested recording language; otherwise return the first active track.
    audio: AudioTrackResponse | None = None
    active_tracks = [t for t in shlok.audio_tracks if t.is_active]
    selected_track = next(
        (
            t
            for t in active_tracks
            if audio_language is not None and t.reciter.language == audio_language.lower()
        ),
        active_tracks[0] if active_tracks else None,
    )
    if selected_track is not None:
        audio = AudioTrackResponse(
            track_id=selected_track.id,
            title=selected_track.title,
            subtitle=selected_track.subtitle,
            language=selected_track.reciter.language,
            url=build_audio_url(selected_track.path),
            duration_sec=selected_track.duration_sec,
            size_bytes=selected_track.size_bytes,
            version=selected_track.version,
            peaks=selected_track.peaks,
        )

    # User-specific enrichment
    is_favorite: bool | None = None
    progress: ProgressResponse | None = None

    if user_id is not None:
        fav = await db.scalar(
            select(Favorite).where(
                Favorite.user_id == user_id,
                Favorite.shlok_id == shlok.id,
            )
        )
        is_favorite = fav is not None

        prog = await db.scalar(
            select(ListenProgress).where(
                ListenProgress.user_id == user_id,
                ListenProgress.shlok_id == shlok.id,
            )
        )
        if prog is not None:
            progress = ProgressResponse(
                last_position_sec=prog.last_position_sec,
                completed=prog.completed,
                listen_count=prog.listen_count,
                last_listened_at=prog.last_listened_at,
            )

    return ShlokDetailResponse(
        chapter=chapter_num,
        verse=verse_num,
        reference=f"{chapter_num}.{verse_num}",
        sanskrit=shlok.sanskrit,
        transliteration=shlok.transliteration,
        content=content,
        audio=audio,
        is_favorite=is_favorite,
        progress=progress,
    )


# ---------------------------------------------------------------------------
# Topics / Reciters
# ---------------------------------------------------------------------------


async def get_topics(db: AsyncSession) -> list[TopicResponse]:
    """Return all content topics ordered by sort_order."""
    result = await db.execute(
        select(Topic).order_by(Topic.sort_order.asc())
    )
    topics = result.scalars().all()
    return [
        TopicResponse(
            id=t.id,
            slug=t.slug,
            name_en=t.name_en,
            name_hi=t.name_hi,
        )
        for t in topics
    ]


async def get_reciters(db: AsyncSession) -> list[ReciterResponse]:
    """Return all reciters."""
    result = await db.execute(select(Reciter).order_by(Reciter.name.asc()))
    reciters = result.scalars().all()
    return [
        ReciterResponse(
            id=r.id,
            name=r.name,
            language=r.language,
            bio=r.bio,
        )
        for r in reciters
    ]


# ---------------------------------------------------------------------------
# Featured chapter
# ---------------------------------------------------------------------------


async def get_featured_chapter(
    db: AsyncSession,
    week: int | None = None,
    user_id: int | None = None,
) -> FeaturedChapterResponse:
    """Return a chapter recommended for the current pregnancy week.

    Fallback order:
      1. ``WeekTheme.recommended_chapter`` for the given week.
      2. First chapter by sort order (general fallback).

    Args:
        week: Pregnancy week (1-40). If ``None``, uses the general fallback.
        user_id: Authenticated user's ID for progress enrichment.

    Raises:
        NotFoundError: If no chapters are available at all.
    """
    reason = "Start your Gita journey with this foundational chapter."
    chapter: Chapter | None = None

    if week is not None:
        theme = await db.scalar(
            select(WeekTheme)
            .options(
                selectinload(WeekTheme.recommended_chapter)
                .selectinload(Chapter.topics)
                .selectinload(ChapterTopic.topic),
            )
            .where(WeekTheme.week == week)
        )
        if theme and theme.recommended_chapter:
            chapter = theme.recommended_chapter
            reason = (
                f"Recommended for week {week} — "
                f"{theme.title_en}: {theme.description_en[:120]}"
            )

    # Fallback: first chapter by sort order
    if chapter is None:
        stmt = (
            select(Chapter)
            .options(
                selectinload(Chapter.topics).selectinload(ChapterTopic.topic),
            )
            .order_by(Chapter.sort_order.asc(), Chapter.number.asc())
            .limit(1)
        )
        chapter = await db.scalar(stmt)

    if chapter is None:
        raise NotFoundError("No chapters available.")

    progress_map: dict[int, ChapterProgressBrief] = {}
    if user_id is not None:
        progress_map = await _build_chapter_progress_map(db, user_id)

    return FeaturedChapterResponse(
        chapter=_chapter_to_response(chapter, progress_map.get(chapter.id)),
        reason=reason,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _chapter_to_response(
    chapter: Chapter,
    user_progress: ChapterProgressBrief | None = None,
) -> ChapterResponse:
    """Map a ``Chapter`` ORM instance to a ``ChapterResponse``."""
    return ChapterResponse(
        id=chapter.id,
        number=chapter.number,
        name_sanskrit=chapter.name_sanskrit,
        name_transliterated=chapter.name_transliterated,
        name_en=chapter.name_en,
        verses_count=chapter.verses_count,
        summary_en=chapter.summary_en,
        summary_hi=chapter.summary_hi,
        maternal_theme_en=chapter.maternal_theme_en,
        maternal_theme_hi=chapter.maternal_theme_hi,
        recommended_trimester=chapter.recommended_trimester,
        topics=[
            TopicResponse(
                id=ct.topic.id,
                slug=ct.topic.slug,
                name_en=ct.topic.name_en,
                name_hi=ct.topic.name_hi,
            )
            for ct in chapter.topics
        ],
        user_progress=user_progress,
    )


def _shlok_to_brief(shlok: Shlok, chapter_number: int) -> ShlokBrief:
    """Map a ``Shlok`` ORM instance to a compact ``ShlokBrief``."""
    return ShlokBrief(
        chapter=chapter_number,
        verse=shlok.verse_number,
        reference=f"{chapter_number}.{shlok.verse_number}",
        sanskrit=shlok.sanskrit,
        transliteration=shlok.transliteration,
        has_audio=any(t.is_active for t in shlok.audio_tracks),
    )


async def _build_chapter_progress_map(
    db: AsyncSession,
    user_id: int,
) -> dict[int, ChapterProgressBrief]:
    """Build a mapping from chapter_id → progress summary for a user.

    Counts distinct shloks where ``completed = True`` per chapter.
    """
    stmt = (
        select(
            Shlok.chapter_id,
            func.count(ListenProgress.id).label("heard"),
        )
        .join(ListenProgress, ListenProgress.shlok_id == Shlok.id)
        .where(
            ListenProgress.user_id == user_id,
            ListenProgress.completed.is_(True),
        )
        .group_by(Shlok.chapter_id)
    )
    result = await db.execute(stmt)
    rows = result.all()

    # We also need total verses per chapter
    chapter_stmt = select(Chapter.id, Chapter.verses_count)
    ch_result = await db.execute(chapter_stmt)
    totals = {row.id: row.verses_count for row in ch_result.all()}

    progress_map: dict[int, ChapterProgressBrief] = {}
    for row in rows:
        chapter_id = row.chapter_id
        total = totals.get(chapter_id, 1)
        progress_map[chapter_id] = ChapterProgressBrief(
            heard=min(row.heard, total),
            total=total,
        )

    return progress_map
