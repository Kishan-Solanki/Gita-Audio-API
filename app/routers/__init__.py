"""Router initialization and exports."""

from app.routers.admin import router as admin_router
from app.routers.audio import router as audio_router
from app.routers.auth import router as auth_router
from app.routers.chapters import router as chapters_router
from app.routers.daily import router as daily_router
from app.routers.health import router as health_router
from app.routers.me import router as me_router
from app.routers.search import router as search_router
from app.routers.shloks import router as shloks_router
from app.routers.weeks import router as weeks_router

__all__ = [
    "admin_router",
    "audio_router",
    "auth_router",
    "chapters_router",
    "daily_router",
    "health_router",
    "me_router",
    "search_router",
    "shloks_router",
    "weeks_router",
]
