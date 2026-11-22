"""Streak service: non-guilt streak tracking with one grace day.

Design philosophy ("non-guilt"):
  - A single missed day does NOT break the streak (one grace day).
  - Two consecutive missed days reset the streak to 0.
  - Language is always encouraging: no "you lost your streak" messaging.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SanskarCompletion
from app.schemas.pregnancy import StreakResponse


async def get_streak(
    db: AsyncSession,
    user_id: int,
) -> StreakResponse:
    """Compute streak statistics for a user.

    Returns:
        ``StreakResponse`` with:
          - **current_streak**: consecutive days with at most one grace day.
          - **days_this_week**: distinct completion dates in the last 7 days.
          - **total_completed**: all-time completion count.
    """
    # 1. Total completed (all-time count of records)
    total_completed: int = (
        await db.scalar(
            select(func.count(SanskarCompletion.id)).where(
                SanskarCompletion.user_id == user_id,
            )
        )
    ) or 0

    # 2. Distinct completion dates, descending (for streak calculation)
    dates_stmt = (
        select(distinct(SanskarCompletion.date))
        .where(SanskarCompletion.user_id == user_id)
        .order_by(SanskarCompletion.date.desc())
    )
    result = await db.execute(dates_stmt)
    completion_dates: list[date] = [row[0] for row in result.all()]

    # 3. Current streak with one grace day
    current_streak = _compute_streak_with_grace(completion_dates)

    # 4. Days this week: distinct dates in the last 7 calendar days
    today = date.today()
    week_start = today - timedelta(days=6)  # inclusive window of 7 days
    days_this_week: int = (
        await db.scalar(
            select(func.count(distinct(SanskarCompletion.date))).where(
                SanskarCompletion.user_id == user_id,
                SanskarCompletion.date >= week_start,
                SanskarCompletion.date <= today,
            )
        )
    ) or 0

    return StreakResponse(
        current_streak=current_streak,
        days_this_week=days_this_week,
        total_completed=total_completed,
    )


def _compute_streak_with_grace(dates: list[date]) -> int:
    """Walk backwards through sorted-descending distinct dates.

    Rules:
      - Start from today.  If the most recent completion is not today or
        yesterday, the streak is 0.
      - Walk backwards; allow at most one "gap" (single missing day)
        between consecutive completion dates.
      - Two consecutive missed days end the streak.

    Each completion date counts as 1 toward the streak length, so the
    streak number equals "days on which the user completed", not
    calendar days spanned.
    """
    if not dates:
        return 0

    today = date.today()
    latest = dates[0]

    # Must have completed today or yesterday to have an active streak
    gap_from_today = (today - latest).days
    if gap_from_today > 1:
        return 0

    streak = 1
    grace_used = gap_from_today == 1  # already used grace if latest is yesterday

    for i in range(1, len(dates)):
        gap = (dates[i - 1] - dates[i]).days

        if gap == 1:
            # Consecutive day — extend the streak
            streak += 1
        elif gap == 2 and not grace_used:
            # Single-day gap — use grace day, still extend
            grace_used = True
            streak += 1
        else:
            # Two or more consecutive misses — streak ends
            break

    return streak
