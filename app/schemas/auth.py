"""Authentication request / response schemas."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    """Payload for user registration."""

    model_config = ConfigDict(from_attributes=True)

    email: EmailStr = Field(..., description="User's email address.")
    password: str = Field(..., min_length=8, description="Password (min 8 characters).")
    display_name: str = Field(..., min_length=1, max_length=100, description="User's display name.")


class LoginRequest(BaseModel):
    """Payload for email/password login."""

    model_config = ConfigDict(from_attributes=True)

    email: EmailStr = Field(..., description="Registered email address.")
    password: str = Field(..., description="Account password.")


class RefreshRequest(BaseModel):
    """Payload for refreshing an access token."""

    model_config = ConfigDict(from_attributes=True)

    refresh_token: str = Field(..., description="Previously issued refresh token.")


class TokenResponse(BaseModel):
    """Returned on successful authentication or token refresh."""

    model_config = ConfigDict(from_attributes=True)

    access_token: str = Field(..., description="Short-lived JWT access token.")
    refresh_token: str = Field(..., description="Long-lived refresh token.")
    token_type: str = Field(default="bearer", description="Token scheme (always 'bearer').")
