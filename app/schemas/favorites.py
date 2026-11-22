"""Favorite shlok schemas."""

from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict, Field


class FavoriteResponse(BaseModel):
    """A single favorited shlok."""

    model_config = ConfigDict(from_attributes=True)

    shlok_id: int = Field(..., description="Unique shlok identifier.")
    chapter: int = Field(..., ge=1, description="Chapter number.")
    verse: int = Field(..., ge=1, description="Verse number within the chapter.")
    reference: str = Field(..., examples=["2.47"], description="Chapter.verse reference string.")
    sanskrit_snippet: str = Field(..., description="Short excerpt of the Sanskrit text.")
    meaning_snippet: str = Field(..., description="Brief meaning or translation excerpt.")
    created_at: datetime.datetime = Field(..., description="Timestamp when the shlok was favorited (UTC).")


class FavoriteListResponse(BaseModel):
    """Paginated list of user favorites."""

    model_config = ConfigDict(from_attributes=True)

    favorites: list[FavoriteResponse] = Field(default_factory=list, description="Favorited shloks.")
    total: int = Field(..., ge=0, description="Total number of favorites.")
