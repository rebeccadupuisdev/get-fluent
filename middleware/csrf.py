"""CSRF protection middleware using double-submit cookie pattern."""

import secrets
from urllib.parse import parse_qsl
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

CSRF_COOKIE_NAME = "csrftoken"
CSRF_HEADER_NAME = "X-CSRF-Token"
CSRF_FORM_FIELD = "csrf_token"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


def _parse_form_token(body: bytes, content_type: str | None) -> str | None:
    """Extract csrf_token from form body without consuming the stream for downstream."""
    if not content_type:
        return None
    ct = content_type.lower()
    if "application/x-www-form-urlencoded" in ct:
        parsed = parse_qsl(body.decode("utf-8", errors="replace"))
        return dict(parsed).get(CSRF_FORM_FIELD)
    if "multipart/form-data" in ct:
        # Multipart: find part named csrf_token, value is after blank line
        name_b = f'name="{CSRF_FORM_FIELD}"'.encode()
        if name_b not in body:
            return None
        idx = body.find(name_b)
        part = body[idx:idx + 500]
        parts = part.split(b"\r\n\r\n", 1)
        if len(parts) < 2:
            parts = part.split(b"\n\n", 1)
        if len(parts) >= 2:
            value = parts[1].split(b"\r\n")[0].split(b"\n")[0].decode("utf-8", errors="replace").strip()
            return value or None
    return None


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Validate CSRF token on unsafe methods.
    Token is read from X-CSRF-Token header or form field 'csrf_token'.
    Token must match the csrftoken cookie.
    Uses body() to avoid consuming the stream so downstream handlers can parse the form.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        token = request.cookies.get(CSRF_COOKIE_NAME) or secrets.token_urlsafe(32)
        request.state.csrf_token = token

        if request.method in SAFE_METHODS:
            response = await call_next(request)
            if not request.cookies.get(CSRF_COOKIE_NAME):
                response.set_cookie(
                    key=CSRF_COOKIE_NAME,
                    value=token,
                    httponly=False,  # JS needs to read it for HTMX header
                    secure=request.url.scheme == "https",
                    samesite="lax",
                    path="/",
                )
            return response

        # Unsafe method: validate token
        submitted = (
            request.headers.get(CSRF_HEADER_NAME)
            or request.headers.get("X-CSRFToken")
        )
        if not submitted:
            body = await request.body()
            submitted = _parse_form_token(body, request.headers.get("Content-Type"))
        if not submitted or not secrets.compare_digest(submitted, token):
            return Response(status_code=403, content="CSRF validation failed")

        return await call_next(request)
