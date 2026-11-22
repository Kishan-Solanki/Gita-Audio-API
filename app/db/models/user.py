"""User-domain models: User, RefreshToken, Favorite, ListenProgress, SanskarCompletion."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.content import Shlok


# ── User ─────────────────────────────────────────────────────────────────


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    preferred_lang: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    pregnancy_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="Asia/Kolkata")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # relationships
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", lazy="selectin", cascade="all, delete-orphan"
    )
    favorites: Mapped[list["Favorite"]] = relationship(
        back_populates="user", lazy="selectin", cascade="all, delete-orphan"
    )
    listen_progress: Mapped[list["ListenProgress"]] = relationship(
        back_populates="user", lazy="selectin", cascade="all, delete-orphan"
    )
    sanskar_completions: Mapped[list["SanskarCompletion"]] = relationship(
        back_populates="user", lazy="selectin", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_users_email", "email"),
    )


# ── RefreshToken ─────────────────────────────────────────────────────────


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # relationships
    user: Mapped["User"] = relationship(back_populates="refresh_tokens")

    __table_args__ = (
        Index("ix_refresh_tokens_user_id", "user_id"),
        Index("ix_refresh_tokens_token_hash", "token_hash"),
    )

    # immutable; revoked_at is the only mutable field but we keep updated_at out
    updated_at = None  # type: ignore[assignment]


# ── Favorite (many-to-many user ↔ shlok) ─────────────────────────────────


class Favorite(Base):
    __tablename__ = "favorites"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    shlok_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("shloks.id", ondelete="CASCADE"), primary_key=True
    )

    # relationships
    user: Mapped["User"] = relationship(back_populates="favorites")
    shlok: Mapped["Shlok"] = relationship()

    # join table — no updated_at
    updated_at = None  # type: ignore[assignment]


# ── ListenProgress ───────────────────────────────────────────────────────


class ListenProgress(Base):
    __tablename__ = "listen_progress"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    shlok_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("shloks.id", ondelete="CASCADE"), nullable=False
    )
    last_position_sec: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    listen_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_listened_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # relationships
    user: Mapped["User"] = relationship(back_populates="listen_progress")
    shlok: Mapped["Shlok"] = relationship()

    __table_args__ = (
        UniqueConstraint("user_id", "shlok_id", name="uq_listen_progress_user_shlok"),
        Index("ix_listen_progress_user_id", "user_id"),
    )


# ── SanskarCompletion ────────────────────────────────────────────────────


class SanskarCompletion(Base):
    __tablename__ = "sanskar_completions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    shlok_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("shloks.id", ondelete="CASCADE"), nullable=False
    )
    reflection_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # relationships
    user: Mapped["User"] = relationship(back_populates="sanskar_completions")
    shlok: Mapped["Shlok"] = relationship()

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_sanskar_completions_user_date"),
        Index("ix_sanskar_completions_user_date", "user_id", "date"),
    )

    # immutable
    updated_at = None  # type: ignore[assignment]
