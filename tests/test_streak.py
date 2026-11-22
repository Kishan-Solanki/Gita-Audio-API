"""Unit tests for the non-guilt streak calculation logic with 1-day grace period."""

import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.pregnancy import StreakResponse
from app.services.streak_service import get_streak


@pytest.mark.asyncio
async def test_streak_zero_completions() -> None:
    """User with zero completions has a streak of 0."""
    mock_db = AsyncMock()
    # Mock empty dates
    mock_scalar = AsyncMock(return_value=[])
    mock_db.scalars.return_value = MagicMock(all=lambda: [])

    with patch("app.services.streak_service.select"):
        res = await get_streak(mock_db, user_id=1)
        assert res.current_streak == 0
        assert res.total_completed == 0
        assert res.days_this_week == 0
from unittest.mock import MagicMock
