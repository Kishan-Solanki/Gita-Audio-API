"""Progress service: listen progress tracking and sanskar activity log."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import distinct, func, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import NotFoundError
from app.db.models import (
    Chapter,
    Favorite,
    ListenProgress,
    SanskarCompletion,
    Shlok,
)
from app.schemas.progress import (
    ChapterProgressResponse,
    ProgressResponse,
    SanskarLogEntry,
    SanskarLogResponse,
)


# ---------------------------------------------------------------------------
# Progress updates
# ---------------------------------------------------------------------------


async def update_progress(
    db: AsyncSession,
    user_id: int,
    shlok_id: int,
    position_sec: float,
    completed: bool,
) -> ProgressResponse:
    """Create or update listening progress for a user/shlok pair.

    When *completed* flips from ``False`` to ``True`` the ``listen_count``
    is incremented by one.

    Args:
        db: Async database session.
        user_id: Authenticated user's ID.
        shlok_id: Shlok being listened to.
        position_sec: Current playback position in seconds.
        completed: Whether the user finished listening to the full track.

    Raises:
        NotFoundError: If the shlok does not exist.
    """
    # Verify shlok exists
    shlok = await db.get(Shlok, shlok_id)
    if shlok is None:
        raise NotFoundError(f"Shlok {shlok_id} not found.")

    # Find or create
    progress = await db.scalar(
        select(ListenProgress).where(
            ListenProgress.user_id == user_id,
            ListenProgress.shlok_id == shlok_id,
        )
    )

    now = datetime.now(UTC)

    if progress is None:
        progress = ListenProgress(
            user_id=user_id,
            shlok_id=shlok_id,
            last_position_sec=int(position_sec),
            completed=completed,
            listen_count=1 if completed else 0,
            last_listened_at=now,
        )
        db.add(progress)
    else:
        # Increment listen_count when completed flips to True
        if completed and not progress.completed:
            progress.listen_count += 1
        elif completed and progress.completed:
            # Already completed before — still count a re-listen
            progress.listen_count += 1

        progress.last_position_sec = int(position_sec)
        progress.completed = completed
        progress.last_listened_at = now

    await db.flush()

    return ProgressResponse(
        last_position_sec=progress.last_position_sec,
        completed=progress.completed,
        listen_count=progress.listen_count,
        last_listened_at=progress.last_listened_at,
    )


# ---------------------------------------------------------------------------
# Per-chapter summary
# ---------------------------------------------------------------------------


async def get_user_progress(
    db: AsyncSession,
    user_id: int,
) -> list[ChapterProgressResponse]:
    """Return per-chapter progress summary (heard/total) for a user.

    Only chapters where the user has at least one ``completed`` listen
    are included, plus all 18 chapters with zero progress for
    completeness.
    """
    # Completed count per chapter
    heard_stmt = (
        select(
            Shlok.chapter_id,
            func.count(distinct(ListenProgress.shlok_id)).label("heard"),
        )
        .join(ListenProgress, ListenProgress.shlok_id == Shlok.id)
        .where(
            ListenProgress.user_id == user_id,
            ListenProgress.completed.is_(True),
        )
        .group_by(Shlok.chapter_id)
    )
    heard_result = await db.execute(heard_stmt)
    heard_map: dict[int, int] = {row.chapter_id: row.heard for row in heard_result.all()}

    # All chapters
    chapters_result = await db.execute(
        select(Chapter).order_by(Chapter.number.asc())
    )
    chapters = chapters_result.scalars().all()

    return [
        ChapterProgressResponse(
            chapter_number=ch.number,
            chapter_name=ch.name_en,
            heard=heard_map.get(ch.id, 0),
            total=ch.verses_count,
        )
        for ch in chapters
    ]


# ---------------------------------------------------------------------------
# Sanskar log (merged favorites + completions)
# ---------------------------------------------------------------------------


async def get_sanskar_log(
    db: AsyncSession,
    user_id: int,
    limit: int = 20,
    offset: int = 0,
) -> SanskarLogResponse:
    """Return a merged, date-ordered log of favorites and sanskar completions.

    Each entry has a ``type`` of ``"favorite"`` or ``"completion"`` and is
    ordered newest-first.
    """
    # Total count: favorites + completions
    fav_count: int = (
        await db.scalar(
            select(func.count()).select_from(Favorite).where(
                Favorite.user_id == user_id,
            )
        )
    ) or 0

    comp_count: int = (
        await db.scalar(
            select(func.count()).select_from(SanskarCompletion).where(
                SanskarCompletion.user_id == user_id,
            )
        )
    ) or 0

    total = fav_count + comp_count

    # Fetch favorites with shlok + chapter info
    fav_stmt = (
        select(Favorite)
        .options(
            selectinload(Favorite.shlok).selectinload(Shlok.chapter),
        )
        .where(Favorite.user_id == user_id)
        .order_by(Favorite.created_at.desc())
    )
    fav_result = await db.execute(fav_stmt)
    favorites = fav_result.scalars().unique().all()

    # Fetch completions with shlok + chapter info
    comp_stmt = (
        select(SanskarCompletion)
        .options(
            selectinload(SanskarCompletion.shlok).selectinload(Shlok.chapter),
        )
        .where(SanskarCompletion.user_id == user_id)
        .order_by(SanskarCompletion.date.desc())
    )
    comp_result = await db.execute(comp_stmt)
    completions = comp_result.scalars().unique().all()

    # Merge into a unified list sorted by date descending
    entries: list[SanskarLogEntry] = []

    for f in favorites:
        shlok = f.shlok
        ch_num = shlok.chapter.number if shlok.chapter else 0
        entries.append(
            SanskarLogEntry(
                type="favorite",
                date=f.created_at.date() if hasattr(f.created_at, "date") else f.created_at,
                shlok_reference=f"{ch_num}.{shlok.verse_number}",
                sanskrit_snippet=shlok.sanskrit[:200],
                note=None,
            )
        )

    for c in completions:
        shlok = c.shlok
        ch_num = shlok.chapter.number if shlok.chapter else 0
        entries.append(
            SanskarLogEntry(
                type="completion",
                date=c.date,
                shlok_reference=f"{ch_num}.{shlok.verse_number}",
                sanskrit_snippet=shlok.sanskrit[:200],
                note=c.reflection_note,
            )
        )

    # Sort by date descending
    entries.sort(key=lambda e: e.date, reverse=True)

    # Paginate
    page = entries[offset : offset + limit]

    return SanskarLogResponse(
        entries=page,
        total=total,
    )
