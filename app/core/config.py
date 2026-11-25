"""Application configuration via pydantic-settings."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Database ────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/gita"

    @property
    def async_database_url(self) -> str:
        """Ensure database URL uses asyncpg driver even if Render provides postgresql:// or postgres://."""
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    # ── JWT ──────────────────────────────────────────────────────────────
    JWT_SECRET: str = "CHANGE-ME-IN-PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_MINUTES: int = 30
    REFRESH_TOKEN_DAYS: int = 30

    # ── Audio ────────────────────────────────────────────────────────────
    AUDIO_ROOT: str = "/data/audio"
    AUDIO_BASE_URL: str = "http://localhost:8000/audio"

    # ── CORS ─────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = Field(default=["*"])

    # ── General ──────────────────────────────────────────────────────────
    ENV: str = "development"
    APP_NAME: str = "Garbh Journey API"
    API_V1_PREFIX: str = "/api/v1"


settings = Settings()
