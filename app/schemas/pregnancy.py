"""Pregnancy journey and daily sanskar schemas."""

from __future__ import annotations

import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.content import ShlokBrief, ShlokDetailResponse


# ---------------------------------------------------------------------------
# Streak
# ---------------------------------------------------------------------------

class StreakResponse(BaseModel):
    """User's sanskar streak statistics."""

    model_config = ConfigDict(from_attributes=True)

    current_streak: int = Field(..., ge=0, description="Consecutive days with at least one completion.")
    days_this_week: int = Field(..., ge=0, le=7, description="Days completed in the current calendar week.")
    total_completed: int = Field(..., ge=0, description="All-time completion count.")


# ---------------------------------------------------------------------------
# Pregnancy week
# ---------------------------------------------------------------------------

class WeekBrief(BaseModel):
    """Compact pregnancy-week summary for list views."""

    model_config = ConfigDict(from_attributes=True)

    week: int = Field(..., ge=1, le=42, description="Pregnancy week number.")
    title_en: str = Field(..., description="Week title in English.")
    title_hi: str = Field(..., description="Week title in Hindi.")
    trimester: int = Field(..., ge=1, le=3, description="Trimester (1, 2, or 3).")


class WeekDetailResponse(BaseModel):
    """Detailed pregnancy-week guidance including recommended shloks."""

    model_config = ConfigDict(from_attributes=True)

    week: int = Field(..., ge=1, le=42, description="Pregnancy week number.")
    theme_key: str = Field(..., description="Thematic key for the week (e.g. 'inner_peace').")
    title_en: str = Field(..., description="Week title in English.")
    title_hi: str = Field(..., description="Week title in Hindi.")
    description_en: str = Field(..., description="Week description in English.")
    description_hi: str = Field(..., description="Week description in Hindi.")
    trimester: int = Field(..., ge=1, le=3, description="Trimester (1, 2, or 3).")
    recommended_shloks: list[ShlokBrief] = Field(
        default_factory=list, description="Shloks recommended for this week."
    )


# ---------------------------------------------------------------------------
# Daily Sanskar
# ---------------------------------------------------------------------------

class DailySanskarResponse(BaseModel):
    """Today's recommended sanskar (shlok + guidance)."""

    model_config = ConfigDict(from_attributes=True)

    shlok: ShlokDetailResponse = Field(..., description="The shlok recommended for today.")
    reflection_prompt: Optional[str] = Field(None, description="Guided reflection question.")
    bonding_practice: Optional[str] = Field(None, description="Suggested bonding activity.")
    completed_today: bool = Field(..., description="Whether the user has completed today's sanskar.")
    streak: StreakResponse = Field(..., description="User's current streak statistics.")
    needs_pregnancy_date: bool = Field(
        ..., description="True if the user has not yet set a pregnancy start date."
    )


class SanskarCompleteRequest(BaseModel):
    """Payload sent when the user marks a daily sanskar as completed."""

    model_config = ConfigDict(from_attributes=True)

    shlok_id: int = Field(..., description="ID of the completed shlok.")
    reflection_note: Optional[str] = Field(
        None, max_length=2000, description="Optional personal reflection note."
    )


class SanskarCompleteResponse(BaseModel):
    """Confirmation returned after recording a sanskar completion."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Completion record ID.")
    date: datetime.date = Field(..., description="Date the completion was recorded.")
    shlok_id: int = Field(..., description="Completed shlok ID.")
    reflection_note: Optional[str] = Field(None, description="User's reflection note, if provided.")
