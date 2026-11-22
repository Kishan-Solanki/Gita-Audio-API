"""Content-domain models: Chapter, Shlok, ShlokContent, Topic, Reciter, AudioTrack."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.pregnancy import WeekTheme


# ── Enums ────────────────────────────────────────────────────────────────


class AudioKind(str, enum.Enum):
    shlok = "shlok"
    chapter = "chapter"
    meditation = "meditation"


# ── Chapter ──────────────────────────────────────────────────────────────


class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    number: Mapped[int] = mapped_column(
        SmallInteger,
        unique=True,
        nullable=False,
        comment="Gita chapter number 1-18",
    )
    name_sanskrit: Mapped[str] = mapped_column(String(255), nullable=False)
    name_transliterated: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    verses_count: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    summary_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    summary_hi: Mapped[str] = mapped_column(Text, nullable=False, default="")
    maternal_theme_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    maternal_theme_hi: Mapped[str] = mapped_column(Text, nullable=False, default="")
    recommended_trimester: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # relationships
    shloks: Mapped[list["Shlok"]] = relationship(back_populates="chapter", lazy="selectin")
    audio_tracks: Mapped[list["AudioTrack"]] = relationship(back_populates="chapter", lazy="selectin")
    topics: Mapped[list["ChapterTopic"]] = relationship(back_populates="chapter", lazy="selectin")
    week_themes: Mapped[list["WeekTheme"]] = relationship(back_populates="recommended_chapter", lazy="selectin")

    __table_args__ = (
        CheckConstraint("number >= 1 AND number <= 18", name="chapter_number_range"),
        Index("ix_chapters_number", "number"),
    )


# ── Shlok ────────────────────────────────────────────────────────────────


class Shlok(Base):
    __tablename__ = "shloks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    chapter_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False
    )
    verse_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    sanskrit: Mapped[str] = mapped_column(Text, nullable=False)
    transliteration: Mapped[str] = mapped_column(Text, nullable=False)
    speaker: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # relationships
    chapter: Mapped["Chapter"] = relationship(back_populates="shloks")
    contents: Mapped[list["ShlokContent"]] = relationship(back_populates="shlok", lazy="selectin")
    audio_tracks: Mapped[list["AudioTrack"]] = relationship(back_populates="shlok", lazy="selectin")
    topics: Mapped[list["ShlokTopic"]] = relationship(back_populates="shlok", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("chapter_id", "verse_number", name="uq_shloks_chapter_verse"),
        Index(
            "ix_shloks_transliteration_gin",
            "transliteration",
            postgresql_using="gin",
            postgresql_ops={"transliteration": "gin_trgm_ops"},
        ),
    )

    # override updated_at: shlok records are immutable after creation
    updated_at = None  # type: ignore[assignment]


# ── ShlokContent ─────────────────────────────────────────────────────────


class ShlokContent(Base):
    __tablename__ = "shlok_contents"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    shlok_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("shloks.id", ondelete="CASCADE"), nullable=False
    )
    lang: Mapped[str] = mapped_column(String(10), nullable=False, comment="ISO 639-1 code")
    literal_meaning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    simple_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reflection_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bonding_practice: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # relationships
    shlok: Mapped["Shlok"] = relationship(back_populates="contents")

    __table_args__ = (
        UniqueConstraint("shlok_id", "lang", name="uq_shlok_contents_shlok_lang"),
        Index(
            "ix_shlok_contents_literal_meaning_gin",
            "literal_meaning",
            postgresql_using="gin",
            postgresql_ops={"literal_meaning": "gin_trgm_ops"},
        ),
        Index(
            "ix_shlok_contents_simple_explanation_gin",
            "simple_explanation",
            postgresql_using="gin",
            postgresql_ops={"simple_explanation": "gin_trgm_ops"},
        ),
    )


# ── Topic ────────────────────────────────────────────────────────────────


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    name_hi: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # relationships
    chapters: Mapped[list["ChapterTopic"]] = relationship(back_populates="topic", lazy="selectin")
    shloks: Mapped[list["ShlokTopic"]] = relationship(back_populates="topic", lazy="selectin")

    # topic records are immutable after creation
    updated_at = None  # type: ignore[assignment]


# ── ChapterTopic (many-to-many) ─────────────────────────────────────────


class ChapterTopic(Base):
    __tablename__ = "chapter_topics"

    chapter_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("chapters.id", ondelete="CASCADE"), primary_key=True
    )
    topic_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True
    )

    chapter: Mapped["Chapter"] = relationship(back_populates="topics")
    topic: Mapped["Topic"] = relationship(back_populates="chapters")

    # no updated_at for join table
    updated_at = None  # type: ignore[assignment]


# ── ShlokTopic (many-to-many) ───────────────────────────────────────────


class ShlokTopic(Base):
    __tablename__ = "shlok_topics"

    shlok_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("shloks.id", ondelete="CASCADE"), primary_key=True
    )
    topic_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True
    )

    shlok: Mapped["Shlok"] = relationship(back_populates="topics")
    topic: Mapped["Topic"] = relationship(back_populates="shloks")

    updated_at = None  # type: ignore[assignment]


# ── Reciter ──────────────────────────────────────────────────────────────


class Reciter(Base):
    __tablename__ = "reciters"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    language: Mapped[str] = mapped_column(String(50), nullable=False)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # relationships
    audio_tracks: Mapped[list["AudioTrack"]] = relationship(back_populates="reciter", lazy="selectin")

    # reciter records are immutable after creation
    updated_at = None  # type: ignore[assignment]


# ── AudioTrack ───────────────────────────────────────────────────────────


class AudioTrack(Base):
    __tablename__ = "audio_tracks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    kind: Mapped[AudioKind] = mapped_column(
        Enum(AudioKind, name="audio_kind", native_enum=True),
        nullable=False,
    )
    shlok_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("shloks.id", ondelete="SET NULL"), nullable=True
    )
    chapter_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True
    )
    reciter_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("reciters.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    subtitle: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    duration_sec: Mapped[int] = mapped_column(Integer, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    bitrate_kbps: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    peaks: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # type: ignore[type-arg]
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # relationships
    shlok: Mapped[Optional["Shlok"]] = relationship(back_populates="audio_tracks")
    chapter: Mapped[Optional["Chapter"]] = relationship(back_populates="audio_tracks")
    reciter: Mapped["Reciter"] = relationship(back_populates="audio_tracks")

    __table_args__ = (
        Index("ix_audio_tracks_kind", "kind"),
        Index("ix_audio_tracks_shlok_id", "shlok_id"),
        Index("ix_audio_tracks_chapter_id", "chapter_id"),
    )
