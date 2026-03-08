"""Unit tests for auth.deps module."""

from unittest.mock import MagicMock

from auth.security import create_session_token
from auth.deps import get_optional_auth


def test_get_optional_auth_with_valid_cookie_returns_email():
    """Returns email when valid session cookie is present."""
    token = create_session_token("test@example.com")
    request = MagicMock()
    request.cookies = MagicMock()
    request.cookies.get.return_value = token

    result = get_optional_auth(request)

    assert result == "test@example.com"


def test_get_optional_auth_without_cookie_returns_none():
    """Returns None when no auth cookie is present."""
    request = MagicMock()
    request.cookies = MagicMock()
    request.cookies.get.return_value = None

    result = get_optional_auth(request)

    assert result is None
