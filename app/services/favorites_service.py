"""Favorites service: add, remove, and list favorited shloks."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import NotFoundError
from app.db.models import Chapter, Favorite, Shlok, ShlokContent
from app.schemas.favorites import FavoriteListResponse, FavoriteResponse


async def get_favorites(
    db: AsyncSession,
    user_id: int,
    limit: int = 20,
    offset: int = 0,
) -> FavoriteListResponse:
    """Return a paginated list of a user's favorited shloks.

    Results are ordered by most-recently-favorited first.
    """
    # Total count
    total: int = (
        await db.scalar(
            select(func.count()).select_from(Favorite).where(
                Favorite.user_id == user_id,
            )
        )
    ) or 0

    # Paginated fetch with shlok + chapter eager loading
    stmt = (
        select(Favorite)
        .options(
            selectinload(Favorite.shlok)
            .selectinload(Shlok.contents),
            selectinload(Favorite.shlok)
            .joinedload(Shlok.chapter),
        )
        .where(Favorite.user_id == user_id)
        .order_by(Favorite.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    favorites = result.scalars().unique().all()

    return FavoriteListResponse(
        favorites=[_favorite_to_response(f) for f in favorites],
        total=total,
    )


async def add_favorite(
    db: AsyncSession,
    user_id: int,
    shlok_id: int,
) -> FavoriteResponse:
    """Add a shlok to the user's favorites (idempotent).

    If the shlok is already favorited, the existing favorite is returned.

    Raises:
        NotFoundError: If the shlok does not exist.
    """
    # Verify shlok exists
    shlok = await db.scalar(
        select(Shlok)
        .options(selectinload(Shlok.contents), selectinload(Shlok.chapter))
        .where(Shlok.id == shlok_id)
    )
    if shlok is None:
        raise NotFoundError(f"Shlok {shlok_id} not found.")

    # Idempotent: check if already favorited
    existing = await db.scalar(
        select(Favorite)
        .options(
            selectinload(Favorite.shlok)
            .selectinload(Shlok.contents),
            selectinload(Favorite.shlok)
            .joinedload(Shlok.chapter),
        )
        .where(Favorite.user_id == user_id, Favorite.shlok_id == shlok_id)
    )
    if existing is not None:
        return _favorite_to_response(existing)

    fav = Favorite(user_id=user_id, shlok_id=shlok_id)
    db.add(fav)
    await db.flush()

    # Reload with relationships
    loaded = await db.scalar(
        select(Favorite)
        .options(
            selectinload(Favorite.shlok)
            .selectinload(Shlok.contents),
            selectinload(Favorite.shlok)
            .joinedload(Shlok.chapter),
        )
        .where(Favorite.user_id == user_id, Favorite.shlok_id == shlok_id)
    )
    return _favorite_to_response(loaded)  # type: ignore[arg-type]


async def remove_favorite(
    db: AsyncSession,
    user_id: int,
    shlok_id: int,
) -> None:
    """Remove a shlok from the user's favorites (idempotent).

    If the shlok is not currently favorited, this is a no-op.
    """
    fav = await db.scalar(
        select(Favorite).where(
            Favorite.user_id == user_id,
            Favorite.shlok_id == shlok_id,
        )
    )
    if fav is not None:
        await db.delete(fav)
        await db.flush()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _favorite_to_response(fav: Favorite) -> FavoriteResponse:
    """Map a ``Favorite`` ORM instance to a ``FavoriteResponse`` schema."""
    shlok = fav.shlok
    chapter_num = shlok.chapter.number if shlok.chapter else 0

    # Pick the best available meaning snippet
    meaning = ""
    for c in shlok.contents:
        if c.simple_explanation:
            meaning = c.simple_explanation[:200]
            break
        if c.literal_meaning:
            meaning = c.literal_meaning[:200]
            break

    return FavoriteResponse(
        shlok_id=shlok.id,
        chapter=chapter_num,
        verse=shlok.verse_number,
        reference=f"{chapter_num}.{shlok.verse_number}",
        sanskrit_snippet=shlok.sanskrit[:200],
        meaning_snippet=meaning,
        created_at=fav.created_at,
    )
