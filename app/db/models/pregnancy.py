"""Pregnancy-domain models: WeekTheme, WeekShlok."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.content import Chapter, Shlok


# ── WeekTheme ────────────────────────────────────────────────────────────


class WeekTheme(Base):
    __tablename__ = "week_themes"

    week: Mapped[int] = mapped_column(
        SmallInteger,
        primary_key=True,
        comment="Pregnancy week 1-40",
    )
    theme_key: Mapped[str] = mapped_column(String(100), nullable=False)
    title_en: Mapped[str] = mapped_column(String(255), nullable=False)
    title_hi: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    description_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    description_hi: Mapped[str] = mapped_column(Text, nullable=False, default="")
    trimester: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    recommended_chapter_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("chapters.id", ondelete="SET NULL"),
        nullable=True,
    )

    # relationships
    recommended_chapter: Mapped[Optional["Chapter"]] = relationship(
        back_populates="week_themes",
    )
    week_shloks: Mapped[list["WeekShlok"]] = relationship(
        back_populates="week_theme",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint("week >= 1 AND week <= 40", name="week_range"),
        CheckConstraint("trimester >= 1 AND trimester <= 3", name="trimester_range"),
    )

    # WeekTheme uses `week` as PK; override auto updated_at
    updated_at = None  # type: ignore[assignment]


# ── WeekShlok ────────────────────────────────────────────────────────────


class WeekShlok(Base):
    __tablename__ = "week_shloks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    week: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("week_themes.week", ondelete="CASCADE"),
        nullable=False,
    )
    shlok_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("shloks.id", ondelete="CASCADE"),
        nullable=False,
    )
    day_order: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        comment="Day within the week, 1-7",
    )

    # relationships
    week_theme: Mapped["WeekTheme"] = relationship(back_populates="week_shloks")
    shlok: Mapped["Shlok"] = relationship()

    __table_args__ = (
        UniqueConstraint("week", "day_order", name="uq_week_shloks_week_day"),
        CheckConstraint("day_order >= 1 AND day_order <= 7", name="day_order_range"),
    )

    # immutable join record
    updated_at = None  # type: ignore[assignment]
