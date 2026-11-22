"""Import English and Hindi translations, maternal explanations, and reflection prompts."""

from __future__ import annotations

import argparse
import asyncio
import csv
import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.models.content import Chapter, Shlok, ShlokContent
from app.db.session import async_session_factory


async def import_translations(csv_path: Path, dry_run: bool = False) -> None:
    if not csv_path.exists():
        print(f"File not found: {csv_path}")
        return

    print(f"Reading translations from: {csv_path}")
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Found {len(rows)} translation rows.")

    if dry_run:
        print("[DRY-RUN] No changes committed.")
        return

    async with async_session_factory() as db:
        # Load chapter id mapping
        ch_res = await db.execute(select(Chapter))
        ch_map = {c.number: c.id for c in ch_res.scalars().all()}

        imported = 0
        for r in rows:
            ch_num = int(r["chapter"])
            v_num = int(r["verse"])
            lang = r["lang"].strip()

            if ch_num not in ch_map:
                print(f"Skipping unknown chapter {ch_num}")
                continue

            # Look up shlok
            stmt = select(Shlok).where(
                Shlok.chapter_id == ch_map[ch_num],
                Shlok.verse_number == v_num,
            )
            shlok = (await db.execute(stmt)).scalar_one_or_none()
            if shlok is None:
                # If shlok record does not exist yet, create placeholder shlok
                shlok = Shlok(
                    chapter_id=ch_map[ch_num],
                    verse_number=v_num,
                    sanskrit="",
                    transliteration="",
                )
                db.add(shlok)
                await db.flush()

            # Upsert ShlokContent
            c_stmt = select(ShlokContent).where(
                ShlokContent.shlok_id == shlok.id,
                ShlokContent.lang == lang,
            )
            content = (await db.execute(c_stmt)).scalar_one_or_none()
            if content is None:
                content = ShlokContent(
                    shlok_id=shlok.id,
                    lang=lang,
                    literal_meaning=r.get("literal_meaning"),
                    simple_explanation=r.get("simple_explanation"),
                    reflection_prompt=r.get("reflection_prompt"),
                    bonding_practice=r.get("bonding_practice"),
                )
                db.add(content)
            else:
                content.literal_meaning = r.get("literal_meaning")
                content.simple_explanation = r.get("simple_explanation")
                content.reflection_prompt = r.get("reflection_prompt")
                content.bonding_practice = r.get("bonding_practice")
            imported += 1

        await db.commit()
        print(f"Successfully imported/updated {imported} shlok translation records.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import shlok translations")
    parser.add_argument(
        "--file",
        type=Path,
        default=Path("data/seed/translations_template.csv"),
        help="Path to translations CSV",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate without committing")
    args = parser.parse_args()

    asyncio.run(import_translations(args.file, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
