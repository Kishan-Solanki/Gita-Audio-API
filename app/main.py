"""Main FastAPI application factory for Garbh Journey — Gita Audio API."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.logging import RequestIDMiddleware, setup_logging
from app.routers import (
    admin_router,
    audio_router,
    auth_router,
    chapters_router,
    daily_router,
    health_router,
    me_router,
    search_router,
    shloks_router,
    weeks_router,
)

TAGS_METADATA = [
    {
        "name": "Health",
        "description": "Liveness and database readiness probes.",
    },
    {
        "name": "Auth",
        "description": "User registration, authentication, token rotation, and logout.",
    },
    {
        "name": "Profile",
        "description": "User profile management, pregnancy timeline configuration, favorites, and streak.",
    },
    {
        "name": "Library",
        "description": "Bhagavad Gita 18 chapters, summaries, maternal themes, and audio playlists.",
    },
    {
        "name": "Shloks",
        "description": "Individual shlok recitation, Devanagari text, transliteration, meanings, and audio.",
    },
    {
        "name": "Search",
        "description": "Full-text and verse-reference search across Sanskrit, transliteration, and meanings.",
    },
    {
        "name": "Pregnancy",
        "description": "40-week Garbh Sanskar timeline, themes, and recommended shloks.",
    },
    {
        "name": "Daily Sanskar",
        "description": "Today's personalized shlok, maternal reflection, bonding practice, and completion.",
    },
    {
        "name": "Audio & Manifest",
        "description": "Audio caching manifests, offline download support, and reciter metadata.",
    },
    {
        "name": "Admin",
        "description": "Editorial content management and audio rescan triggers (admin only).",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager."""
    setup_logging(json_output=(settings.ENV != "development"))
    yield


def create_app() -> FastAPI:
    """Instantiate and configure the FastAPI application."""
    app = FastAPI(
        title="Garbh Journey — Gita Audio API",
        description=(
            "REST API and audio streaming backend for Garbh Journey, a mobile pregnancy "
            "(Garbh Sanskar) app centered on the 18 chapters and 701 shloks of the selected catalog."
        ),
        version="1.0.0",
        openapi_tags=TAGS_METADATA,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # ── Middleware ───────────────────────────────────────────────────────
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Exception handlers ───────────────────────────────────────────────
    register_exception_handlers(app)

    # ── Health checks (available at both root and under /api/v1) ───────────
    app.include_router(health_router)

    # ── API v1 Routers ────────────────────────────────────────────────────
    v1 = settings.API_V1_PREFIX
    app.include_router(health_router, prefix=v1)
    app.include_router(auth_router, prefix=v1)
    app.include_router(me_router, prefix=v1)
    app.include_router(chapters_router, prefix=v1)
    app.include_router(shloks_router, prefix=v1)
    app.include_router(search_router, prefix=v1)
    app.include_router(weeks_router, prefix=v1)
    app.include_router(daily_router, prefix=v1)
    app.include_router(audio_router, prefix=v1)
    app.include_router(admin_router, prefix=v1)

    # ── Local static audio files (for dev environments) ───────────────────
    if os.path.exists(settings.AUDIO_ROOT):
        app.mount("/audio", StaticFiles(directory=settings.AUDIO_ROOT), name="audio")

    return app


app = create_app()
