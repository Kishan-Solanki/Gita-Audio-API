"""Library chapter endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from app.deps import DBSession, OptionalUser, Pagination
from app.schemas.content import (
    ChapterListResponse,
    ChapterResponse,
    FeaturedChapterResponse,
    PlaylistTrackResponse,
    ShlokBrief,
    TopicResponse,
)
from app.services.audio_url_service import get_chapter_playlist
from app.services.content_service import (
    get_chapter,
    get_chapter_shloks,
    get_chapters,
    get_featured_chapter,
    get_topics,
)

router = APIRouter(tags=["Library"])


@router.get(
    "/chapters",
    response_model=ChapterListResponse,
    summary="List all 18 chapters",
)
async def list_chapters(
    db: DBSession,
    optional_user: OptionalUser,
    topic: Optional[str] = Query(None, description="Filter by topic slug"),
    lang: str = Query("en", description="Preferred language (en, hi)"),
) -> ChapterListResponse:
    """Return all 18 Gita chapters with themes, verse counts, and user progress if authenticated."""
    user_id = optional_user.id if optional_user else None
    return await get_chapters(db, topic_slug=topic, user_id=user_id, lang=lang)


@router.get(
    "/chapters/featured",
    response_model=FeaturedChapterResponse,
    summary="Get featured chapter for current trimester/week",
)
async def featured_chapter(
    db: DBSession,
    optional_user: OptionalUser,
    week: Optional[int] = Query(
        None, ge=1, le=40, description="Override pregnancy week (1-40)"
    ),
) -> FeaturedChapterResponse:
    """Return the featured chapter tailored to the user's current pregnancy week or trimester."""
    user_id = optional_user.id if optional_user else None
    return await get_featured_chapter(db, week=week, user_id=user_id)


@router.get(
    "/chapters/{n}",
    response_model=ChapterResponse,
    summary="Get chapter detail",
)
async def chapter_detail(
    n: int,
    db: DBSession,
    lang: str = Query("en", description="Preferred language (en, hi)"),
) -> ChapterResponse:
    """Return details for chapter `n` (1-18) including summary and maternal themes."""
    return await get_chapter(db, chapter_number=n, lang=lang)


@router.get(
    "/chapters/{n}/shloks",
    response_model=list[ShlokBrief],
    summary="Get paginated shloks for a chapter",
)
async def chapter_shloks(
    n: int,
    db: DBSession,
    pagination: Pagination,
    lang: str = Query("en", description="Preferred language (en, hi)"),
) -> list[ShlokBrief]:
    """Return a paginated list of shlok briefs for chapter `n`."""
    return await get_chapter_shloks(
        db,
        chapter_number=n,
        limit=pagination.limit,
        offset=pagination.offset,
        lang=lang,
    )


@router.get(
    "/chapters/{n}/playlist",
    response_model=list[PlaylistTrackResponse],
    summary="Get audio playlist for chapter",
)
async def chapter_playlist(
    n: int,
    db: DBSession,
    language: Optional[str] = Query(None, min_length=2, max_length=10),
) -> list[PlaylistTrackResponse]:
    """Return chapter and verse tracks, optionally filtered by language (e.g. en, hi, sa)."""
    return await get_chapter_playlist(db, chapter_number=n, language=language)


@router.get(
    "/topics",
    response_model=list[TopicResponse],
    summary="List all content topics",
)
async def list_topics(db: DBSession) -> list[TopicResponse]:
    """Return all filter topics (e.g. calm, devotion, courage, wisdom)."""
    return await get_topics(db)
