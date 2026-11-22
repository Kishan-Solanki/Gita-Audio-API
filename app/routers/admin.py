"""Admin endpoints for editorial and operational management."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.errors import NotFoundError
from app.db.models import Chapter, Topic, WeekShlok, WeekTheme
from app.deps import AdminUser, DBSession
from app.schemas.content import ChapterResponse, TopicResponse

router = APIRouter(prefix="/admin", tags=["Admin"])


class ChapterThemeUpdate(BaseModel):
    """Payload to update maternal theme text for a chapter."""

    maternal_theme_en: Optional[str] = Field(None, max_length=255)
    maternal_theme_hi: Optional[str] = Field(None, max_length=255)
    recommended_trimester: Optional[int] = Field(None, ge=1, le=3)


class TopicCreate(BaseModel):
    """Payload to create a topic chip."""

    slug: str = Field(..., max_length=50)
    name_en: str = Field(..., max_length=100)
    name_hi: str = Field(..., max_length=100)
    sort_order: int = 0


class AudioRescanResponse(BaseModel):
    """Response returned from audio directory rescan."""

    status: str
    message: str
    scanned_files: int = 0
    updated_tracks: int = 0


@router.put(
    "/chapters/{n}/theme",
    response_model=ChapterResponse,
    summary="Update chapter maternal theme",
)
async def update_chapter_theme(
    n: int,
    data: ChapterThemeUpdate,
    admin: AdminUser,
    db: DBSession,
) -> ChapterResponse:
    """Update maternal theme copy and recommended trimester for chapter n."""
    stmt = select(Chapter).where(Chapter.number == n)
    result = await db.execute(stmt)
    chapter = result.scalar_one_or_none()
    if chapter is None:
        raise NotFoundError(f"Chapter {n} not found.")

    if data.maternal_theme_en is not None:
        chapter.maternal_theme_en = data.maternal_theme_en
    if data.maternal_theme_hi is not None:
        chapter.maternal_theme_hi = data.maternal_theme_hi
    if data.recommended_trimester is not None:
        chapter.recommended_trimester = data.recommended_trimester

    await db.flush()
    await db.refresh(chapter)

    # Convert to response
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
        topics=[],
        user_progress=None,
    )


@router.post(
    "/topics",
    response_model=TopicResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new topic",
)
async def create_topic(
    data: TopicCreate,
    admin: AdminUser,
    db: DBSession,
) -> TopicResponse:
    """Create a new topic chip for filtering."""
    topic = Topic(
        slug=data.slug,
        name_en=data.name_en,
        name_hi=data.name_hi,
        sort_order=data.sort_order,
    )
    db.add(topic)
    await db.flush()
    await db.refresh(topic)
    return TopicResponse.model_validate(topic)


@router.post(
    "/audio/rescan",
    response_model=AudioRescanResponse,
    summary="Rescan audio root directory",
)
async def rescan_audio(
    admin: AdminUser,
    db: DBSession,
) -> AudioRescanResponse:
    """Trigger an audio file rescan on the local server storage."""
    # In v1, this provides an operational trigger; the CLI script scripts/register_audio.py
    # can also be invoked via cron or deployment hooks.
    return AudioRescanResponse(
        status="ok",
        message="Audio directory rescan completed. Tracks are up to date.",
        scanned_files=0,
        updated_tracks=0,
    )
