"""Pytest configuration and shared test fixtures."""

from __future__ import annotations

import datetime
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, hash_password
from app.db.models.user import User
from app.main import app


@pytest.fixture
def mock_user() -> User:
    """Fixture providing a sample authenticated expectant mother user."""
    return User(
        id=1,
        email="mother@example.com",
        password_hash=hash_password("SuperSecret123"),
        display_name="Ananya Sharma",
        preferred_lang="en",
        pregnancy_start_date=datetime.date(2026, 3, 1),
        due_date=datetime.date(2026, 12, 7),
        timezone="Asia/Kolkata",
        is_active=True,
        is_admin=False,
    )


@pytest.fixture
def valid_auth_token(mock_user: User) -> str:
    """JWT bearer token for mock_user."""
    return create_access_token(
        subject=str(mock_user.id),
        email=mock_user.email,
        is_admin=mock_user.is_admin,
    )


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client bound to FastAPI application."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
