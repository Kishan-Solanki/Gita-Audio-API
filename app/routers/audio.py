"""Audio manifest and reciter endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.core.config import settings
from app.core.errors import NotFoundError
from app.deps import DBSession
from app.db.models import AudioTrack, Reciter
from app.schemas.content import ReciterResponse
from app.schemas.manifest import ManifestResponse
from app.services.audio_url_service import (
    get_chapter_manifest,
    get_week_manifest,
)
from app.services.content_service import get_reciters

router = APIRouter(tags=["Audio & Manifest"])


@router.get(
    "/audio/shloks/{chapter}/{verse}",
    response_class=RedirectResponse,
    status_code=307,
    summary="Stream a downloaded shlok recitation",
)
async def stream_shlok_audio(chapter: int, verse: int) -> RedirectResponse:
    """Redirect to nginx or the local static mount for byte-range audio delivery."""
    if not 1 <= chapter <= 18 or verse < 1:
        raise NotFoundError("Shlok audio not found.")
    relative_path = f"ch{chapter:02d}/sl{verse:02d}.mp3"
    audio_file = Path(settings.AUDIO_ROOT) / relative_path
    if not audio_file.is_file():
        raise NotFoundError("Shlok audio not found.")
    from app.services.audio_url_service import build_audio_url

    return RedirectResponse(url=build_audio_url(relative_path), status_code=307)


@router.get(
    "/manifest/chapters/{n}",
    response_model=ManifestResponse,
    summary="Get audio manifest for a chapter",
)
async def chapter_audio_manifest(
    n: int,
    db: DBSession,
    language: str | None = Query(None, min_length=2, max_length=10),
) -> ManifestResponse:
    """Return all audio track hashes, sizes, and versions for chapter n so mobile clients

    can sync and cache audio offline.
    """
    return await get_chapter_manifest(db, chapter_number=n, language=language)


@router.get(
    "/manifest/weeks/{n}",
    response_model=ManifestResponse,
    summary="Get audio manifest for a pregnancy week",
)
async def week_audio_manifest(
    n: int,
    db: DBSession,
    language: str | None = Query(None, min_length=2, max_length=10),
) -> ManifestResponse:
    """Return audio tracks for all shloks mapped to pregnancy week n."""
    return await get_week_manifest(db, week=n, language=language)


@router.get(
    "/reciters",
    response_model=list[ReciterResponse],
    summary="List available reciters",
)
async def list_reciters(db: DBSession) -> list[ReciterResponse]:
    """Return all registered audio reciters and voice artists."""
    return await get_reciters(db)


@router.get(
    "/audio/languages",
    response_model=list[str],
    summary="List languages with active audio tracks",
)
async def list_audio_languages(db: DBSession) -> list[str]:
    """Return language codes for which at least one active recording is available."""
    result = await db.execute(
        select(Reciter.language)
        .join(AudioTrack, AudioTrack.reciter_id == Reciter.id)
        .where(AudioTrack.is_active.is_(True))
        .distinct()
        .order_by(Reciter.language.asc())
    )
    return list(result.scalars().all())
