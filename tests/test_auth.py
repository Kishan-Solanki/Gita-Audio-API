"""Authentication and token encryption tests."""

import pytest

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hashing() -> None:
    """Test bcrypt password hashing and verification."""
    password = "MySecurePassword123!"
    pw_hash = hash_password(password)

    assert pw_hash != password
    assert verify_password(password, pw_hash) is True
    assert verify_password("WrongPassword", pw_hash) is False


def test_jwt_access_token_creation_and_decoding() -> None:
    """Test generating and decoding JWT access tokens."""
    token = create_access_token(
        subject="42",
        email="test@garbhjourney.com",
        is_admin=False,
    )
    payload = decode_token(token)

    assert payload["sub"] == "42"
    assert payload["email"] == "test@garbhjourney.com"
    assert payload["type"] == "access"
    assert payload["is_admin"] is False


def test_jwt_refresh_token_creation() -> None:
    """Test generating refresh tokens."""
    token = create_refresh_token(subject="42")
    payload = decode_token(token)

    assert payload["sub"] == "42"
    assert payload["type"] == "refresh"
