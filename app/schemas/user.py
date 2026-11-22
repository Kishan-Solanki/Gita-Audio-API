"""User profile request / response schemas."""

from __future__ import annotations

import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserResponse(BaseModel):
    """Public representation of a user profile."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique user identifier.")
    email: EmailStr = Field(..., description="User's email address.")
    display_name: str = Field(..., description="User's display name.")
    preferred_lang: str = Field(..., examples=["en", "hi"], description="Preferred content language (ISO 639-1).")
    pregnancy_start_date: Optional[datetime.date] = Field(
        None, description="Start date of the current pregnancy (LMP), if set."
    )
    due_date: Optional[datetime.date] = Field(None, description="Estimated due date, if set.")
    timezone: str = Field(..., examples=["Asia/Kolkata"], description="IANA timezone identifier.")


class UserUpdateRequest(BaseModel):
    """Partial-update payload for a user profile.

    Only supplied fields are updated; omitted fields are left unchanged.
    """

    model_config = ConfigDict(from_attributes=True)

    display_name: Optional[str] = Field(None, min_length=1, max_length=100, description="New display name.")
    preferred_lang: Optional[str] = Field(None, examples=["en", "hi"], description="Preferred content language.")
    pregnancy_start_date: Optional[datetime.date] = Field(None, description="Pregnancy start (LMP) date.")
    due_date: Optional[datetime.date] = Field(None, description="Estimated due date.")
    timezone: Optional[str] = Field(None, examples=["Asia/Kolkata"], description="IANA timezone identifier.")
