"""Unit tests for pregnancy week calculation logic."""

import datetime
from unittest.mock import MagicMock

import pytest

from app.services.daily_sanskar_service import _current_week


def test_week_from_due_date_exact() -> None:
    """Test week calculation derived from due date."""
    today = datetime.date(2026, 6, 1)
    # 28 days until due -> 40 - ceil(28/7) = 40 - 4 = 36
    user = MagicMock()
    user.due_date = today + datetime.timedelta(days=28)
    user.pregnancy_start_date = None

    week = _current_week(user, today)
    assert week == 36


def test_week_from_due_date_clamping() -> None:
    """Verify week is clamped between 1 and 40."""
    today = datetime.date(2026, 6, 1)

    # Far future due date (e.g. 300 days) -> clamped to week 1
    user_early = MagicMock()
    user_early.due_date = today + datetime.timedelta(days=300)
    user_early.pregnancy_start_date = None
    assert _current_week(user_early, today) == 1

    # Past due date -> clamped to week 40
    user_late = MagicMock()
    user_late.due_date = today - datetime.timedelta(days=5)
    user_late.pregnancy_start_date = None
    assert _current_week(user_late, today) == 40


def test_week_from_start_date() -> None:
    """Test week calculation derived from pregnancy start date (LMP)."""
    today = datetime.date(2026, 6, 1)
    # 14 days since start -> floor(14/7) + 1 = 3
    user = MagicMock()
    user.due_date = None
    user.pregnancy_start_date = today - datetime.timedelta(days=14)

    week = _current_week(user, today)
    assert week == 3


def test_week_fallback_when_no_dates_set() -> None:
    """If neither date is set, return None to trigger fallback sequence."""
    today = datetime.date(2026, 6, 1)
    user = MagicMock()
    user.due_date = None
    user.pregnancy_start_date = None

    assert _current_week(user, today) is None
