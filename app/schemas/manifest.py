"""Offline manifest schemas for bulk audio download."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ManifestTrack(BaseModel):
    """Metadata for a single downloadable audio track."""

    model_config = ConfigDict(from_attributes=True)

    track_id: int = Field(..., description="Unique audio track identifier.")
    shlok_id: Optional[int] = Field(None, description="Associated shlok ID, if applicable.")
    language: str = Field(..., description="Language code of the recording.")
    url: str = Field(..., description="Download URL for the audio file.")
    size_bytes: int = Field(..., ge=0, description="File size in bytes.")
    sha256: str = Field(..., description="SHA-256 hex digest for integrity verification.")
    version: int = Field(..., ge=1, description="Track version number for cache-busting.")


class ManifestResponse(BaseModel):
    """Full audio manifest returned for offline sync."""

    model_config = ConfigDict(from_attributes=True)

    tracks: list[ManifestTrack] = Field(default_factory=list, description="All downloadable audio tracks.")
    total_size_bytes: int = Field(..., ge=0, description="Combined size of all tracks in bytes.")
