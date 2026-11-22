"""Health and liveness endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.deps import DBSession
from app.schemas.common import HealthReadyResponse, HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse, summary="Liveness check")
async def health_check() -> HealthResponse:
    """Return 200 if the FastAPI application process is up and running."""
    return HealthResponse(status="ok", version="1.0.0")


@router.get(
    "/health/ready",
    response_model=HealthReadyResponse,
    summary="Readiness check",
)
async def readiness_check(db: DBSession) -> HealthReadyResponse:
    """Check database connectivity and return readiness status."""
    try:
        await db.execute(text("SELECT 1"))
        return HealthReadyResponse(
            status="ok", database="connected", version="1.0.0"
        )
    except Exception as exc:
        return HealthReadyResponse(
            status="degraded", database=f"error: {str(exc)}", version="1.0.0"
        )
