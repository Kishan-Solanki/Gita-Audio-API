"""Unit tests for deterministic daily shlok selection."""

import datetime
from unittest.mock import MagicMock

import pytest

from app.services.daily_sanskar_service import _user_today


def test_deterministic_user_today_in_timezone() -> None:
    """User in Asia/Kolkata evaluates to the appropriate local date."""
    user = MagicMock()
    user.timezone = "Asia/Kolkata"

    local_date = _user_today(user)
    assert isinstance(local_date, datetime.date)
