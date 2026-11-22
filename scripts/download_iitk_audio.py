"""Download verse-level Sanskrit recitations from Heritage IITKanpur."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx

BASE_URL = "https://heritage.iitk.ac.in"
VERSE_COUNTS = {
    1: 47, 2: 72, 3: 43, 4: 42, 5: 29, 6: 47,
    7: 30, 8: 28, 9: 34, 10: 42, 11: 55, 12: 20,
    13: 35, 14: 27, 15: 20, 16: 24, 17: 28, 18: 78,
}


def audio_url(chapter: int, verse: int) -> str:
    """Build the MediaWiki hashed-upload URL for a verse's moolam MP3."""
    filename = f"SBG_{chapter}_{verse}_moolam_swmbrhm.mp3"
    digest = hashlib.md5(filename.encode("utf-8")).hexdigest()
    return f"{BASE_URL}/wiki/images/{digest[0]}/{digest[:2]}/{filename}"


def is_mp3(data: bytes, content_type: str) -> bool:
    """Reject HTML error pages and non-MP3 responses."""
    return "audio/" in content_type.lower() or data.startswith(b"ID3") or (
        len(data) > 1 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0
    )


def read_manifest(path: Path) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "source": BASE_URL,
        "recording": "Sanskrit moolam recitation",
        "attribution": "Heritage IITKanpur / Gita Supersite",
        "recordings": [],
    }


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary.replace(path)


def download_audio(
    output_root: Path,
    chapter_filter: int | None = None,
    verse_filter: int | None = None,
    delay: float = 1.0,
) -> tuple[int, int, int]:
    """Fetch direct MP3 URLs and resume from already-downloaded local files."""
    output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = output_root / "iitk_audio_manifest.json"
    manifest = read_manifest(manifest_path)
    known = {
        (item["chapter"], item["verse"]): item
        for item in manifest.get("recordings", [])
    }
    chapters = [chapter_filter] if chapter_filter else range(1, 19)
    downloaded = skipped = missing = failed = 0

    with httpx.Client(
        follow_redirects=True,
        timeout=httpx.Timeout(60.0, connect=20.0),
        headers={"User-Agent": "GarbhJourneyAudioImporter/1.0"},
    ) as client:
        for chapter in chapters:
            if chapter not in VERSE_COUNTS:
                raise ValueError(f"Chapter must be in 1-18, got {chapter}.")
            verses = [verse_filter] if verse_filter else range(1, VERSE_COUNTS[chapter] + 1)

            for verse in verses:
                if verse < 1 or verse > VERSE_COUNTS[chapter]:
                    raise ValueError(f"Invalid verse {chapter}.{verse}.")

                relative = Path(f"ch{chapter:02d}") / f"sl{verse:02d}.mp3"
                destination = output_root / relative
                source_url = audio_url(chapter, verse)

                if destination.exists() and destination.stat().st_size > 0:
                    skipped += 1
                    if (chapter, verse) not in known:
                        data = destination.read_bytes()
                        known[(chapter, verse)] = {
                            "chapter": chapter,
                            "verse": verse,
                            "path": relative.as_posix(),
                            "source_url": source_url,
                            "sha256": hashlib.sha256(data).hexdigest(),
                            "size_bytes": len(data),
                        }
                else:
                    try:
                        response = client.get(source_url)
                        response.raise_for_status()
                        if not is_mp3(response.content, response.headers.get("content-type", "")):
                            raise ValueError(f"Response was not MP3 audio: {source_url}")

                        destination.parent.mkdir(parents=True, exist_ok=True)
                        temporary = destination.with_suffix(".mp3.part")
                        temporary.write_bytes(response.content)
                        temporary.replace(destination)
                        known[(chapter, verse)] = {
                            "chapter": chapter,
                            "verse": verse,
                            "path": relative.as_posix(),
                            "source_url": source_url,
                            "sha256": hashlib.sha256(response.content).hexdigest(),
                            "size_bytes": len(response.content),
                        }
                        downloaded += 1
                        print(f"Downloaded {chapter}.{verse}")
                    except (httpx.HTTPError, ValueError, OSError) as exc:
                        failed += 1
                        print(f"Failed {chapter}.{verse}: {exc}", file=sys.stderr)

                write_manifest(
                    manifest_path,
                    {
                        **manifest,
                        "recordings": sorted(
                            known.values(),
                            key=lambda item: (item["chapter"], item["verse"]),
                        ),
                    },
                )
                time.sleep(delay)

    print(
        f"Finished: {downloaded} downloaded, {skipped} already present, "
        f"{missing} unavailable, {failed} failed. Manifest: {manifest_path}"
    )
    return downloaded, skipped, failed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download IITK Gita verse-level Sanskrit moolam recitations"
    )
    parser.add_argument("--root", type=Path, default=Path("data"))
    parser.add_argument("--chapter", type=int)
    parser.add_argument("--verse", type=int)
    parser.add_argument("--delay", type=float, default=1.0)
    args = parser.parse_args()
    if args.verse is not None and args.chapter is None:
        parser.error("--verse requires --chapter")
    if args.delay < 0:
        parser.error("--delay must be non-negative")
    _, _, failed = download_audio(args.root, args.chapter, args.verse, args.delay)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
