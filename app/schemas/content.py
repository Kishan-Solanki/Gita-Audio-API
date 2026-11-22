"""Content schemas — shloks, chapters, audio tracks, playlists, search, etc."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.progress import ProgressResponse


# ---------------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------------

class AudioTrackResponse(BaseModel):
    """Metadata for a single audio track."""

    model_config = ConfigDict(from_attributes=True)

    track_id: int = Field(..., description="Unique audio track identifier.")
    title: str = Field(..., description="Display title.")
    subtitle: Optional[str] = Field(None, description="Optional subtitle or reciter info.")
    language: str = Field(..., description="Language code of the recording.")
    url: str = Field(..., description="Streaming / download URL.")
    duration_sec: float = Field(..., ge=0, description="Track duration in seconds.")
    size_bytes: int = Field(..., ge=0, description="File size in bytes.")
    version: int = Field(..., ge=1, description="Track version for cache-busting.")
    peaks: Optional[list[float]] = Field(None, description="Waveform peak data for visualization.")


# ---------------------------------------------------------------------------
# Shlok
# ---------------------------------------------------------------------------

class ShlokBrief(BaseModel):
    """Compact shlok representation used in lists and cross-references."""

    model_config = ConfigDict(from_attributes=True)

    chapter: int = Field(..., ge=1, description="Chapter number.")
    verse: int = Field(..., ge=1, description="Verse number.")
    reference: str = Field(..., examples=["2.47"], description="Chapter.verse reference string.")
    sanskrit: str = Field(..., description="Full Sanskrit text of the verse.")
    transliteration: str = Field(..., description="Romanized transliteration.")
    has_audio: bool = Field(..., description="Whether an audio track is available for this verse.")


class ShlokContentResponse(BaseModel):
    """Language-specific content block for a shlok."""

    model_config = ConfigDict(from_attributes=True)

    lang: str = Field(..., examples=["en", "hi"], description="Content language (ISO 639-1).")
    literal_meaning: Optional[str] = Field(None, description="Word-by-word / literal translation.")
    simple_explanation: Optional[str] = Field(None, description="Plain-language explanation.")
    reflection_prompt: Optional[str] = Field(None, description="Guided reflection question for the expectant mother.")
    bonding_practice: Optional[str] = Field(None, description="Suggested bonding activity with the baby.")


class ShlokDetailResponse(BaseModel):
    """Full shlok detail including content, audio, and user-specific state."""

    model_config = ConfigDict(from_attributes=True)

    chapter: int = Field(..., ge=1, description="Chapter number.")
    verse: int = Field(..., ge=1, description="Verse number.")
    reference: str = Field(..., examples=["2.47"], description="Chapter.verse reference string.")
    sanskrit: str = Field(..., description="Full Sanskrit text.")
    transliteration: str = Field(..., description="Romanized transliteration.")
    content: Optional[ShlokContentResponse] = Field(None, description="Localized content for the requested language.")
    audio: Optional[AudioTrackResponse] = Field(None, description="Associated audio track, if available.")
    is_favorite: Optional[bool] = Field(None, description="Whether the current user has favorited this shlok.")
    progress: Optional[ProgressResponse] = Field(None, description="Current user's listening progress.")


# ---------------------------------------------------------------------------
# Topics / Reciters
# ---------------------------------------------------------------------------

class TopicResponse(BaseModel):
    """A content topic or tag."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique topic identifier.")
    slug: str = Field(..., description="URL-safe slug.")
    name_en: str = Field(..., description="Topic name in English.")
    name_hi: str = Field(..., description="Topic name in Hindi.")


class ReciterResponse(BaseModel):
    """An audio reciter / narrator."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique reciter identifier.")
    name: str = Field(..., description="Reciter display name.")
    language: str = Field(..., examples=["sa", "hi"], description="Primary language of recitation.")
    bio: Optional[str] = Field(None, description="Short biography.")


# ---------------------------------------------------------------------------
# Chapter
# ---------------------------------------------------------------------------

class ChapterProgressBrief(BaseModel):
    """Lightweight chapter progress embedded inside ChapterResponse."""

    model_config = ConfigDict(from_attributes=True)

    heard: int = Field(..., ge=0, description="Verses the user has completed.")
    total: int = Field(..., ge=1, description="Total verses in the chapter.")


class ChapterResponse(BaseModel):
    """Full representation of a Gita chapter."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique chapter identifier.")
    number: int = Field(..., ge=1, description="Chapter number (1-18).")
    name_sanskrit: str = Field(..., description="Chapter name in Devanagari.")
    name_transliterated: str = Field(..., description="Romanized chapter name.")
    name_en: str = Field(..., description="English chapter name.")
    verses_count: int = Field(..., ge=1, description="Number of verses in this chapter.")
    summary_en: str = Field(..., description="Chapter summary in English.")
    summary_hi: str = Field(..., description="Chapter summary in Hindi.")
    maternal_theme_en: str = Field(..., description="Maternal wellness theme in English.")
    maternal_theme_hi: str = Field(..., description="Maternal wellness theme in Hindi.")
    recommended_trimester: Optional[int] = Field(
        None, ge=1, le=3, description="Recommended trimester (1, 2, or 3), if any."
    )
    topics: list[TopicResponse] = Field(default_factory=list, description="Topics covered in this chapter.")
    user_progress: Optional[ChapterProgressBrief] = Field(
        None, description="Authenticated user's progress in this chapter."
    )


class ChapterListResponse(BaseModel):
    """List of chapters with total count."""

    model_config = ConfigDict(from_attributes=True)

    chapters: list[ChapterResponse] = Field(default_factory=list, description="Chapter list.")
    total: int = Field(..., ge=0, description="Total number of chapters.")


class FeaturedChapterResponse(BaseModel):
    """A chapter featured/recommended for the user, with a reason."""

    model_config = ConfigDict(from_attributes=True)

    chapter: ChapterResponse = Field(..., description="The featured chapter.")
    reason: str = Field(..., description="Why this chapter is recommended (e.g. trimester relevance).")


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

class SearchShlokResult(BaseModel):
    """A single shlok search hit."""

    model_config = ConfigDict(from_attributes=True)

    chapter: int = Field(..., ge=1, description="Chapter number.")
    verse: int = Field(..., ge=1, description="Verse number.")
    reference: str = Field(..., examples=["2.47"], description="Chapter.verse reference.")
    snippet: str = Field(..., description="Highlighted text snippet matching the query.")
    sanskrit: str = Field(..., description="Full Sanskrit text.")
    transliteration: str = Field(..., description="Romanized transliteration.")


class SearchResultResponse(BaseModel):
    """Aggregated search results across shloks and chapters."""

    model_config = ConfigDict(from_attributes=True)

    shloks: list[SearchShlokResult] = Field(default_factory=list, description="Matching shloks.")
    chapters: list[ChapterResponse] = Field(default_factory=list, description="Matching chapters.")
    total: int = Field(..., ge=0, description="Total number of results across all categories.")


# ---------------------------------------------------------------------------
# Playlist
# ---------------------------------------------------------------------------

class PlaylistTrackResponse(BaseModel):
    """A single track in a generated playlist."""

    model_config = ConfigDict(from_attributes=True)

    track_id: int = Field(..., description="Audio track identifier.")
    shlok_id: Optional[int] = Field(None, description="Associated shlok ID, if applicable.")
    chapter: int = Field(..., ge=1, description="Chapter number.")
    verse: Optional[int] = Field(None, ge=1, description="Verse number, if applicable.")
    title: str = Field(..., description="Track display title.")
    language: str = Field(..., description="Language code of the recording.")
    url: str = Field(..., description="Streaming / download URL.")
    duration_sec: float = Field(..., ge=0, description="Track duration in seconds.")
