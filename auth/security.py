"""Magic link token generation/verification and email whitelist."""

import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Token config
TOKEN_EXPIRY_MINUTES = 15
TOKEN_ALGORITHM = "HS256"
AUTH_COOKIE_NAME = "auth_token"

# Lazy-loaded from env
_whitelist: set[str] | None = None
_secret: str | None = None


def _get_secret() -> str:
    global _secret
    if _secret is None:
        _secret = os.getenv("AUTH_SECRET", "")
        if not _secret:
            raise ValueError(
                "AUTH_SECRET must be set for magic link auth. "
                "Generate with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
    return _secret


def get_email_whitelist() -> set[str]:
    """Return the set of whitelisted emails (lowercase)."""
    global _whitelist
    if _whitelist is None:
        raw = os.getenv("AUTH_EMAIL_WHITELIST", "")
        _whitelist = {e.strip().lower() for e in raw.split(",") if e.strip()}
    return _whitelist


def is_email_whitelisted(email: str) -> bool:
    """Check if the given email is in the whitelist."""
    return email.strip().lower() in get_email_whitelist()


def create_magic_link_token(email: str) -> str:
    """Create a signed JWT for the magic link. Token expires in TOKEN_EXPIRY_MINUTES."""
    payload = {
        "sub": email.strip().lower(),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRY_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, _get_secret(), algorithm=TOKEN_ALGORITHM)


def verify_magic_link_token(token: str) -> str | None:
    """
    Verify the magic link token and return the email if valid.
    Returns None if token is invalid or expired.
    """
    try:
        payload = jwt.decode(
            token,
            _get_secret(),
            algorithms=[TOKEN_ALGORITHM],
        )
        email = payload.get("sub")
        if email and is_email_whitelisted(email):
            return email
        return None
    except jwt.PyJWTError:
        return None


def create_session_token(email: str) -> str:
    """Create a longer-lived session token (7 days) for cookie storage."""
    payload = {
        "sub": email.strip().lower(),
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, _get_secret(), algorithm=TOKEN_ALGORITHM)


def verify_session_token(token: str) -> str | None:
    """Verify session token and return email if valid."""
    try:
        payload = jwt.decode(
            token,
            _get_secret(),
            algorithms=[TOKEN_ALGORITHM],
        )
        email = payload.get("sub")
        if email and is_email_whitelisted(email):
            return email
        return None
    except jwt.PyJWTError:
        return None


# Security schemes
http_bearer = HTTPBearer(auto_error=False)


async def get_current_user_email(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = None,
) -> str:
    """
    FastAPI dependency: extract and verify auth from Bearer token or cookie.
    Raises HTTPException 401 if not authenticated.
    """
    # Try Bearer token first
    if credentials and credentials.credentials:
        email = verify_session_token(credentials.credentials)
        if email:
            return email

    # Try cookie
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if token:
        email = verify_session_token(token)
        if email:
            return email

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )
