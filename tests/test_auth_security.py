"""Unit tests for auth.security module."""

import os

import pytest

from auth.security import (
    create_magic_link_token,
    create_session_token,
    is_email_whitelisted,
    verify_magic_link_token,
    verify_session_token,
)


def test_is_email_whitelisted_matches():
    """Whitelisted email (from AUTH_EMAIL_WHITELIST) returns True."""
    assert is_email_whitelisted("test@example.com") is True


def test_is_email_whitelisted_case_insensitive():
    """Email matching is case-insensitive."""
    assert is_email_whitelisted("TEST@EXAMPLE.COM") is True


def test_is_email_whitelisted_strips_whitespace():
    """Leading/trailing whitespace is stripped before check."""
    assert is_email_whitelisted("  test@example.com  ") is True


def test_is_email_whitelisted_non_whitelisted_returns_false():
    """Non-whitelisted email returns False."""
    assert is_email_whitelisted("other@example.com") is False


def test_create_and_verify_magic_link_token_roundtrip():
    """Valid magic link token verifies and returns email."""
    token = create_magic_link_token("test@example.com")
    email = verify_magic_link_token(token)
    assert email == "test@example.com"


def test_verify_magic_link_token_invalid_returns_none():
    """Invalid or tampered token returns None."""
    assert verify_magic_link_token("invalid-token") is None


def test_verify_magic_link_token_expired_returns_none():
    """Expired token returns None."""
    import jwt
    from datetime import datetime, timedelta, timezone

    payload = {
        "sub": "test@example.com",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        "iat": datetime.now(timezone.utc) - timedelta(minutes=20),
    }
    secret = os.environ.get("AUTH_SECRET", "test-secret-do-not-use-in-production")
    expired_token = jwt.encode(payload, secret, algorithm="HS256")
    assert verify_magic_link_token(expired_token) is None


def test_create_and_verify_session_token_roundtrip():
    """Valid session token verifies and returns email."""
    token = create_session_token("test@example.com")
    email = verify_session_token(token)
    assert email == "test@example.com"


def test_verify_session_token_invalid_returns_none():
    """Invalid session token returns None."""
    assert verify_session_token("invalid-token") is None
