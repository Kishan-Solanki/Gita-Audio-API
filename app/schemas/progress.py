"""Listening progress and sanskar log schemas."""

from __future__ import annotations

import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ProgressUpdateRequest(BaseModel):
    """Payload sent by the client to update playback progress."""

    model_config = ConfigDict(from_attributes=True)

    position_sec: float = Field(..., ge=0, description="Current playback position in seconds.")
    completed: bool = Field(..., description="Whether the user finished listening to the full track.")


class ProgressResponse(BaseModel):
    """Listening progress for a single track / shlok."""

    model_config = ConfigDict(from_attributes=True)

    last_position_sec: float = Field(..., ge=0, description="Last saved playback position in seconds.")
    completed: bool = Field(..., description="True if the track was listened to completion at least once.")
    listen_count: int = Field(..., ge=0, description="Total number of completed listens.")
    last_listened_at: Optional[datetime.datetime] = Field(
        None, description="Timestamp of the most recent listen event (UTC)."
    )


class ChapterProgressResponse(BaseModel):
    """Aggregate listening progress for a single chapter."""

    model_config = ConfigDict(from_attributes=True)

    chapter_number: int = Field(..., ge=1, description="Chapter number.")
    chapter_name: str = Field(..., description="Chapter display name.")
    heard: int = Field(..., ge=0, description="Number of verses the user has completed in this chapter.")
    total: int = Field(..., ge=1, description="Total number of verses in this chapter.")


class SanskarLogEntry(BaseModel):
    """Single entry in the user's sanskar activity log."""

    model_config = ConfigDict(from_attributes=True)

    type: Literal["favorite", "completion"] = Field(
        ..., description="Kind of activity: 'favorite' or 'completion'."
    )
    date: datetime.date = Field(..., description="Date of the activity.")
    shlok_reference: str = Field(..., examples=["2.47"], description="Chapter.verse reference string.")
    sanskrit_snippet: str = Field(..., description="Short excerpt of the Sanskrit text.")
    note: Optional[str] = Field(None, description="User-supplied reflection note, if any.")


class SanskarLogResponse(BaseModel):
    """Paginated list of sanskar log entries."""

    model_config = ConfigDict(from_attributes=True)

    entries: list[SanskarLogEntry] = Field(default_factory=list, description="Activity log entries.")
    total: int = Field(..., ge=0, description="Total matching entries.")
