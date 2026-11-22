"""Tests for health check and liveness/readiness probes."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_liveness(async_client: AsyncClient) -> None:
    """Test that GET /health returns 200 OK with expected version."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_api_v1_health(async_client: AsyncClient) -> None:
    """Test that GET /api/v1/health also returns 200 OK."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
