"""Seed 40 pregnancy weeks and week-to-shlok mappings."""

from __future__ import annotations

import argparse
import asyncio
import csv
import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.models.content import Chapter, Shlok
from app.db.models.pregnancy import WeekShlok, WeekTheme
from app.db.session import async_session_factory


async def seed_weeks(
    weeks_csv: Path,
    week_shloks_csv: Path,
    dry_run: bool = False,
) -> None:
    print(f"Loading weeks from: {weeks_csv}")
    with open(weeks_csv, "r", encoding="utf-8") as f:
        weeks = list(csv.DictReader(f))

    print(f"Found {len(weeks)} pregnancy weeks.")

    if dry_run:
        print("[DRY-RUN] No changes committed.")
        return

    async with async_session_factory() as db:
        ch_map = {c.number: c.id for c in (await db.execute(select(Chapter))).scalars().all()}

        for w in weeks:
            week_num = int(w["week"])
            raw_rec_ch = w.get("recommended_chapter_number", "")
            rec_ch_num = None
            if raw_rec_ch:
                try:
                    rec_ch_num = int(str(raw_rec_ch).strip())
                except (ValueError, TypeError):
                    rec_ch_num = None
            rec_ch_id = ch_map.get(rec_ch_num) if rec_ch_num else None

            # Calculate trimester: 1-12 -> 1, 13-27 -> 2, 28-40 -> 3
            trimester = 1 if week_num <= 12 else (2 if week_num <= 27 else 3)

            stmt = select(WeekTheme).where(WeekTheme.week == week_num)
            theme = (await db.execute(stmt)).scalar_one_or_none()

            if theme is None:
                theme = WeekTheme(
                    week=week_num,
                    theme_key=w["theme_key"],
                    title_en=w["title_en"],
                    title_hi=w.get("title_hi", ""),
                    description_en=w.get("description_en", ""),
                    description_hi=w.get("description_hi", ""),
                    trimester=trimester,
                    recommended_chapter_id=rec_ch_id,
                )
                db.add(theme)
            else:
                theme.theme_key = w["theme_key"]
                theme.title_en = w["title_en"]
                theme.title_hi = w.get("title_hi", "")
                theme.description_en = w.get("description_en", "")
                theme.description_hi = w.get("description_hi", "")
                theme.trimester = trimester
                theme.recommended_chapter_id = rec_ch_id

        await db.flush()

        # Seed week-to-shlok mappings if file exists
        if week_shloks_csv.exists():
            print(f"Loading week shlok mappings from: {week_shloks_csv}")
            with open(week_shloks_csv, "r", encoding="utf-8") as f:
                mappings = list(csv.DictReader(f))

            mapped_count = 0
            for m in mappings:
                w_num = int(m["week"])
                ch_num = int(m["shlok_chapter"])
                v_num = int(m["shlok_verse"])
                day_order = int(m["day_order"])

                if ch_num not in ch_map:
                    continue

                shlok_stmt = select(Shlok).where(
                    Shlok.chapter_id == ch_map[ch_num],
                    Shlok.verse_number == v_num,
                )
                shlok = (await db.execute(shlok_stmt)).scalar_one_or_none()
                if shlok is None:
                    continue

                ws_stmt = select(WeekShlok).where(
                    WeekShlok.week == w_num,
                    WeekShlok.day_order == day_order,
                )
                ws = (await db.execute(ws_stmt)).scalar_one_or_none()
                if ws is None:
                    ws = WeekShlok(
                        week=w_num,
                        shlok_id=shlok.id,
                        day_order=day_order,
                    )
                    db.add(ws)
                else:
                    ws.shlok_id = shlok.id
                mapped_count += 1

            print(f"Seeded {mapped_count} week shlok mappings.")

        await db.commit()
        print("Week seeding completed.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed pregnancy weeks and mappings")
    parser.add_argument(
        "--weeks",
        type=Path,
        default=Path("data/seed/weeks.csv"),
        help="Path to weeks CSV",
    )
    parser.add_argument(
        "--mappings",
        type=Path,
        default=Path("data/seed/week_shloks.csv"),
        help="Path to week shloks CSV",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate without committing")
    args = parser.parse_args()

    asyncio.run(seed_weeks(args.weeks, args.mappings, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
