"""SQLAlchemy async engine, session factory, and declarative base."""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Any

from sqlalchemy import MetaData, func
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import settings

# ── Naming convention for constraints (Alembic-friendly) ─────────────────

_convention: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=_convention)

# ── Engine & session factory ─────────────────────────────────────────────

engine: AsyncEngine = create_async_engine(
    settings.async_database_url,
    echo=(settings.ENV == "development"),
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Declarative base with timestamp mixin ────────────────────────────────


class Base(AsyncAttrs, DeclarativeBase):
    """Project-wide declarative base.

    Every model inheriting from ``Base`` automatically receives
    ``created_at`` and ``updated_at`` timestamp columns.
    """

    metadata = metadata

    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    def __repr__(self) -> str:  # pragma: no cover
        cols = ", ".join(
            f"{c.key}={getattr(self, c.key)!r}"
            for c in self.__table__.columns  # type: ignore[attr-defined]
            if c.key in ("id", "name", "email", "slug")
        )
        return f"<{type(self).__name__}({cols})>"


__all__ = [
    "Base",
    "engine",
    "async_session_factory",
    "metadata",
]
