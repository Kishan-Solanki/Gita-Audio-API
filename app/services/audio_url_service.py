"""Audio URL building, playlist generation, and manifest services."""

from __future__ import annotations

from urllib.parse import quote

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.errors import NotFoundError
from app.db.models import AudioKind, AudioTrack, Chapter, Reciter, Shlok, WeekShlok
from app.schemas.content import PlaylistTrackResponse
from app.schemas.manifest import ManifestResponse, ManifestTrack


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------


def build_audio_url(path: str) -> str:
    """Construct a full streaming URL from a relative path.

    Example::

        >>> build_audio_url("ch02/verse47.mp3")
        "http://localhost:8000/audio/ch02/verse47.mp3"
    """
    base = settings.AUDIO_BASE_URL.rstrip("/")
    relative = quote(path.lstrip("/"), safe="/")
    return f"{base}/{relative}"


def build_signed_url(path: str, expires_in: int = 3600) -> str:
    """Return a signed URL for the given audio path.

    This is a **placeholder** for future CDN-signed-URL support.
    Currently returns the same public URL as :func:`build_audio_url`.

    Args:
        path: Relative audio file path.
        expires_in: Desired URL lifetime in seconds (unused until signing is wired).
    """
    # TODO: integrate with CDN / cloud-storage signing when ready
    return build_audio_url(path)


# ---------------------------------------------------------------------------
# Playlist
# ---------------------------------------------------------------------------


async def get_chapter_playlist(
    db: AsyncSession,
    chapter_number: int,
    language: str | None = None,
) -> list[PlaylistTrackResponse]:
    """Return an ordered list of audio tracks for a given chapter.

    Tracks are grouped by language, then ordered by verse number with
    full-chapter tracks after verse-level tracks.

    Raises:
        NotFoundError: If the chapter does not exist.
    """
    chapter = await db.scalar(
        select(Chapter).where(Chapter.number == chapter_number)
    )
    if chapter is None:
        raise NotFoundError(f"Chapter {chapter_number} not found.")

    stmt = (
        select(AudioTrack)
        .outerjoin(Shlok, AudioTrack.shlok_id == Shlok.id)
        .join(Reciter, AudioTrack.reciter_id == Reciter.id)
        .where(
            AudioTrack.is_active.is_(True),
            or_(
                AudioTrack.chapter_id == chapter.id,
                and_(Shlok.chapter_id == chapter.id, AudioTrack.kind == AudioKind.shlok),
            ),
        )
        .options(selectinload(AudioTrack.shlok), selectinload(AudioTrack.reciter))
        .order_by(
            Reciter.language.asc(),
            Shlok.verse_number.asc().nulls_last(),
            AudioTrack.id.asc(),
        )
    )
    if language is not None:
        stmt = stmt.where(Reciter.language == language.lower())
    result = await db.execute(stmt)
    tracks = result.scalars().all()

    return [
        PlaylistTrackResponse(
            track_id=t.id,
            shlok_id=t.shlok_id,
            chapter=chapter_number,
            verse=t.shlok.verse_number if t.shlok else None,
            title=t.title,
            language=t.reciter.language,
            url=build_audio_url(t.path),
            duration_sec=t.duration_sec,
        )
        for t in tracks
    ]


# ---------------------------------------------------------------------------
# Manifests
# ---------------------------------------------------------------------------


async def get_chapter_manifest(
    db: AsyncSession,
    chapter_number: int,
    language: str | None = None,
) -> ManifestResponse:
    """Return download-manifest metadata for all active tracks in a chapter.

    Includes size, sha256, and version for offline cache-busting.

    Raises:
        NotFoundError: If the chapter does not exist.
    """
    chapter = await db.scalar(
        select(Chapter).where(Chapter.number == chapter_number)
    )
    if chapter is None:
        raise NotFoundError(f"Chapter {chapter_number} not found.")

    stmt = (
        select(AudioTrack)
        .outerjoin(Shlok, AudioTrack.shlok_id == Shlok.id)
        .join(Reciter, AudioTrack.reciter_id == Reciter.id)
        .where(
            AudioTrack.is_active.is_(True),
            or_(
                AudioTrack.chapter_id == chapter.id,
                and_(Shlok.chapter_id == chapter.id, AudioTrack.kind == AudioKind.shlok),
            ),
        )
        .options(selectinload(AudioTrack.reciter))
        .order_by(AudioTrack.id.asc())
    )
    if language is not None:
        stmt = stmt.where(Reciter.language == language.lower())
    result = await db.execute(stmt)
    tracks = result.scalars().all()

    manifest_tracks = [
        ManifestTrack(
            track_id=t.id,
            shlok_id=t.shlok_id,
            language=t.reciter.language,
            url=build_audio_url(t.path),
            size_bytes=t.size_bytes,
            sha256=t.sha256,
            version=t.version,
        )
        for t in tracks
    ]

    return ManifestResponse(
        tracks=manifest_tracks,
        total_size_bytes=sum(t.size_bytes for t in tracks),
    )


async def get_week_manifest(
    db: AsyncSession,
    week: int,
    language: str | None = None,
) -> ManifestResponse:
    """Return download-manifest metadata for all shlok audio tracks in a pregnancy week.

    Raises:
        NotFoundError: If no week-shlok mappings exist for the given week.
    """
    stmt = (
        select(WeekShlok)
        .options(
            selectinload(WeekShlok.shlok)
            .selectinload(Shlok.audio_tracks)
            .selectinload(AudioTrack.reciter)
        )
        .where(WeekShlok.week == week)
        .order_by(WeekShlok.day_order.asc())
    )
    result = await db.execute(stmt)
    week_shloks = result.scalars().all()

    if not week_shloks:
        raise NotFoundError(f"No shlok mapping found for week {week}.")

    manifest_tracks: list[ManifestTrack] = []
    seen_ids: set[int] = set()

    for ws in week_shloks:
        for t in ws.shlok.audio_tracks:
            if (
                t.is_active
                and t.id not in seen_ids
                and (language is None or t.reciter.language == language.lower())
            ):
                seen_ids.add(t.id)
                manifest_tracks.append(
                    ManifestTrack(
                        track_id=t.id,
                        shlok_id=t.shlok_id,
                        language=t.reciter.language,
                        url=build_audio_url(t.path),
                        size_bytes=t.size_bytes,
                        sha256=t.sha256,
                        version=t.version,
                    )
                )

    return ManifestResponse(
        tracks=manifest_tracks,
        total_size_bytes=sum(t.size_bytes for t in manifest_tracks),
    )
