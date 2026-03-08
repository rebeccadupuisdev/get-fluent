"""FastAPI auth dependencies."""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth.security import (
    AUTH_COOKIE_NAME,
    get_current_user_email,
    http_bearer,
    verify_session_token,
)
from fastapi import Request


async def require_auth(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(http_bearer)],
) -> str:
    """
    Dependency that requires authentication for create/update/delete operations.
    Accepts Bearer token or auth cookie.
    """
    return await get_current_user_email(request, credentials)


def get_optional_auth(request: Request) -> str | None:
    """Check if user is authenticated (for template context)."""
    # Cookie
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if token:
        return verify_session_token(token)
    return None
