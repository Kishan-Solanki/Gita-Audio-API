"""Import and validate Bhagavad Gita chapters and shloks dataset.

Enforces strict verse count validation across all 18 chapters (total 701 shloks):
[47, 72, 43, 42, 29, 47, 30, 28, 34, 42, 55, 20, 35, 27, 20, 24, 28, 78]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.models.content import Chapter, Shlok
from app.db.session import async_session_factory

EXPECTED_VERSE_COUNTS: dict[int, int] = {
    1: 47,
    2: 72,
    3: 43,
    4: 42,
    5: 29,
    6: 47,
    7: 30,
    8: 28,
    9: 34,
    10: 42,
    11: 55,
    12: 20,
    13: 35,
    14: 27,
    15: 20,
    16: 24,
    17: 28,
    18: 78,
}
TOTAL_EXPECTED_VERSES = sum(EXPECTED_VERSE_COUNTS.values())  # 701


async def import_gita_text(
    chapters_path: Path,
    shloks_path: Path | None,
    dry_run: bool = False,
) -> None:
    print(f"Reading chapters from: {chapters_path}")
    with open(chapters_path, "r", encoding="utf-8") as f:
        chapters_data = json.load(f)

    if len(chapters_data) != 18:
        raise ValueError(f"Expected 18 chapters, found {len(chapters_data)}.")

    total_verses = 0
    for ch in chapters_data:
        num = ch["number"]
        expected = EXPECTED_VERSE_COUNTS.get(num)
        actual = ch.get("verses_count")
        if actual != expected:
            raise ValueError(
                f"Chapter {num} verse count mismatch! Expected {expected}, got {actual}."
            )
        total_verses += actual

    if total_verses != TOTAL_EXPECTED_VERSES:
        raise ValueError(
            f"Total verses mismatch! Expected {TOTAL_EXPECTED_VERSES}, got {total_verses}."
        )

    print(f"Validation PASSED: 18 chapters, exactly {total_verses} verses.")

    if dry_run:
        print("[DRY-RUN] No database modifications made.")
        return

    async with async_session_factory() as db:
        print("Upserting chapters into database...")
        for ch in chapters_data:
            num = ch["number"]
            stmt = select(Chapter).where(Chapter.number == num)
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if existing is None:
                existing = Chapter(
                    number=num,
                    name_sanskrit=ch["name_sanskrit"],
                    name_transliterated=ch["name_transliterated"],
                    name_en=ch["name_en"],
                    verses_count=ch["verses_count"],
                    summary_en=ch.get("summary_en"),
                    summary_hi=ch.get("summary_hi"),
                    sort_order=num,
                )
                db.add(existing)
            else:
                existing.name_sanskrit = ch["name_sanskrit"]
                existing.name_transliterated = ch["name_transliterated"]
                existing.name_en = ch["name_en"]
                existing.verses_count = ch["verses_count"]
                existing.summary_en = ch.get("summary_en")
                existing.summary_hi = ch.get("summary_hi")

        await db.flush()

        # If a shloks seed file is provided, import shloks
        if shloks_path and shloks_path.exists():
            print(f"Importing shloks from {shloks_path}...")
            with open(shloks_path, "r", encoding="utf-8") as f:
                shloks_data = json.load(f)
            # Fetch all chapters to map number to id
            ch_res = await db.execute(select(Chapter))
            ch_map = {c.number: c.id for c in ch_res.scalars().all()}

            inserted_shloks = 0
            for item in shloks_data:
                ch_num = item["chapter"]
                v_num = item["verse"]
                ch_id = ch_map[ch_num]

                s_stmt = select(Shlok).where(
                    Shlok.chapter_id == ch_id, Shlok.verse_number == v_num
                )
                shlok_obj = (await db.execute(s_stmt)).scalar_one_or_none()
                if shlok_obj is None:
                    shlok_obj = Shlok(
                        chapter_id=ch_id,
                        verse_number=v_num,
                        sanskrit=item["sanskrit"],
                        transliteration=item.get("transliteration", ""),
                        speaker=item.get("speaker"),
                    )
                    db.add(shlok_obj)
                    inserted_shloks += 1
            print(f"Imported/verified {inserted_shloks} shloks.")

        await db.commit()
        print("Import completed successfully.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Gita chapters and shloks")
    parser.add_argument(
        "--chapters",
        type=Path,
        default=Path("data/seed/chapters.json"),
        help="Path to chapters JSON",
    )
    parser.add_argument(
        "--shloks",
        type=Path,
        default=Path("data/seed/shloks.json"),
        help="Path to shloks JSON (optional)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate without committing")
    args = parser.parse_args()

    asyncio.run(import_gita_text(args.chapters, args.shloks, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
