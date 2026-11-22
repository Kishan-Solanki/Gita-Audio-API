"""Register verse and language-wise chapter MP3 files found under AUDIO_ROOT."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.db.models.content import AudioKind, AudioTrack, Chapter, Reciter, Shlok
from app.db.session import async_session_factory

SHLOK_PATTERN = re.compile(r"^ch(\d{2})/sl(\d{2,3})\.mp3$", re.IGNORECASE)
CHAPTER_PATTERN = re.compile(r"(?:chapter|adhyaya)(\d+)", re.IGNORECASE)
LANGUAGES = {
    "english": ("en", "English"),
    "gujarati": ("gu", "Gujarati"),
    "hindi": ("hi", "Hindi"),
    "marathi": ("mr", "Marathi"),
    "sanskrit": ("sa", "Sanskrit"),
}


def probe_audio_file(file_path: Path) -> tuple[int, int | None]:
    """Return (duration_sec, bitrate_kbps), with a file-size fallback."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet", "-print_format", "json", "-show_format",
                "-show_streams", str(file_path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        info = json.loads(result.stdout).get("format", {})
        duration = int(round(float(info.get("duration", 0))))
        bitrate = int(int(info.get("bit_rate", 0)) / 1000) or None
        return duration, bitrate
    except (OSError, subprocess.SubprocessError, ValueError, json.JSONDecodeError):
        return max(1, round(file_path.stat().st_size / 12_000)), 96


def compute_sha256(file_path: Path) -> str:
    """Compute a streaming SHA-256 digest for a local audio file."""
    digest = hashlib.sha256()
    with file_path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


async def get_reciter(
    db: AsyncSession,
    language: str,
    display_name: str,
) -> Reciter:
    """Find or create the collection reciter for a language."""
    reciter = await db.scalar(
        select(Reciter).where(
            Reciter.language == language,
            Reciter.name == display_name,
        )
    )
    if reciter is None:
        reciter = Reciter(name=display_name, language=language)
        db.add(reciter)
        await db.flush()
    return reciter


async def register_audio(
    audio_root: Path,
    dry_run: bool = False,
) -> None:
    """Upsert supported audio tracks; never changes or removes source files."""
    if not audio_root.exists():
        raise FileNotFoundError(f"AUDIO_ROOT does not exist: {audio_root}")

    files = sorted(audio_root.rglob("*.mp3"))
    print(f"Scanning {len(files)} MP3 files under {audio_root}")

    async with async_session_factory() as db:
        chapters = (await db.execute(select(Chapter))).scalars().all()
        chapter_ids = {chapter.number: chapter.id for chapter in chapters}
        new_count = updated_count = unchanged_count = orphan_count = 0
        reciters: dict[str, Reciter] = {}

        for file_path in files:
            relative_path = file_path.relative_to(audio_root).as_posix()
            shlok_match = SHLOK_PATTERN.fullmatch(relative_path)
            chapter_match = CHAPTER_PATTERN.search(file_path.stem)

            if shlok_match:
                chapter_number, verse_number = map(int, shlok_match.groups())
                chapter_id = chapter_ids.get(chapter_number)
                if chapter_id is None:
                    orphan_count += 1
                    continue
                shlok = await db.scalar(
                    select(Shlok).where(
                        Shlok.chapter_id == chapter_id,
                        Shlok.verse_number == verse_number,
                    )
                )
                if shlok is None:
                    orphan_count += 1
                    continue
                language, label = "sa", "Sanskrit"
                track_kind = AudioKind.shlok
                title = f"Gita {chapter_number}.{verse_number}"
                chapter_id_for_track = None
                shlok_id_for_track = shlok.id
            elif chapter_match and file_path.parent.name.lower() in LANGUAGES:
                chapter_number = int(chapter_match.group(1))
                chapter_id = chapter_ids.get(chapter_number)
                if chapter_id is None:
                    orphan_count += 1
                    continue
                language, label = LANGUAGES[file_path.parent.name.lower()]
                track_kind = AudioKind.chapter
                title = f"Bhagavad Gita Chapter {chapter_number} ({label})"
                chapter_id_for_track = chapter_id
                shlok_id_for_track = None
            else:
                # Introductions, summaries, and devotional tracks remain outside the chapter API.
                continue

            reciter = reciters.get(language)
            if reciter is None:
                reciter = await get_reciter(db, language, f"{label} Audio Collection")
                reciters[language] = reciter

            track_query = select(AudioTrack).where(
                AudioTrack.kind == track_kind,
            )
            if track_kind == AudioKind.shlok:
                track_query = track_query.where(AudioTrack.shlok_id == shlok.id)
            else:
                track_query = track_query.where(
                    AudioTrack.chapter_id == chapter_id,
                    AudioTrack.reciter_id == reciter.id,
                )

            size_bytes = file_path.stat().st_size
            digest = compute_sha256(file_path)
            duration_sec, bitrate_kbps = probe_audio_file(file_path)
            track = await db.scalar(track_query)

            if track is None:
                new_count += 1
                if not dry_run:
                    db.add(
                        AudioTrack(
                            kind=track_kind,
                            shlok_id=shlok_id_for_track,
                            chapter_id=chapter_id_for_track,
                            reciter_id=reciter.id,
                            title=title,
                            subtitle=f"{label} audio",
                            path=relative_path,
                            duration_sec=duration_sec,
                            size_bytes=size_bytes,
                            bitrate_kbps=bitrate_kbps,
                            sha256=digest,
                            version=1,
                            peaks=None,
                            is_active=True,
                        )
                    )
            elif track.sha256 != digest:
                updated_count += 1
                if not dry_run:
                    track.path = relative_path
                    track.reciter_id = reciter.id
                    track.title = title
                    track.subtitle = f"{label} audio"
                    track.size_bytes = size_bytes
                    track.sha256 = digest
                    track.duration_sec = duration_sec
                    track.bitrate_kbps = bitrate_kbps
                    track.version += 1
                    track.is_active = True
            else:
                unchanged_count += 1
                if not dry_run and not track.is_active:
                    track.is_active = True

        if not dry_run:
            await db.commit()

        print("--- Audio registration report ---")
        print(f"New: {new_count}; updated: {updated_count}; unchanged: {unchanged_count}")
        print(f"Unmapped verse files: {orphan_count}")
        if dry_run:
            print("Dry run: database changes were not committed.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Register verse and chapter audio files")
    parser.add_argument("--root", type=Path, default=Path(settings.AUDIO_ROOT))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(register_audio(args.root, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
