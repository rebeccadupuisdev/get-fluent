"""Auth routes: magic link request and verification."""

import os
from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from auth.email_service import send_magic_link_email
from auth.limiter import limiter
from auth.security import (
    AUTH_COOKIE_NAME,
    create_magic_link_token,
    create_session_token,
    is_email_whitelisted,
    verify_magic_link_token,
)
from views.deps import templates, with_csrf

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    """Render the magic link login form."""
    return templates.TemplateResponse(
        request,
        "auth/login.html",
        with_csrf(request, error=None, sent=False),
    )


@router.post("/request-magic-link", response_class=HTMLResponse)
@limiter.limit("5/minute")
async def request_magic_link(
    request: Request,
    email: Annotated[str, Form()],
) -> HTMLResponse:
    """
    If email is whitelisted, generate a magic link and send it.
    Always returns the same UI (no email enumeration).
    """
    email_clean = email.strip().lower()
    sent = False
    error = None

    if is_email_whitelisted(email_clean):
        token = create_magic_link_token(email_clean)
        base_url = (
            os.getenv("APP_BASE_URL") or str(request.base_url)
        ).rstrip("/")
        magic_link = f"{base_url}/auth/verify?token={token}"
        if send_magic_link_email(email_clean, magic_link):
            sent = True
        else:
            error = "Failed to send email. Please try again."
    else:
        # Don't reveal whether email is whitelisted
        sent = True

    return templates.TemplateResponse(
        request,
        "partials/login.html",
        with_csrf(request, error=error, sent=sent),
    )


@router.get("/verify", response_model=None)
@limiter.limit("10/minute")
async def verify_magic_link(
    request: Request,
    token: str | None = None,
) -> RedirectResponse | HTMLResponse:
    """
    Verify the magic link token. On success, set session cookie and redirect to /.
    """
    if not token:
        return RedirectResponse(url="/auth/login", status_code=302)

    email = verify_magic_link_token(token)
    if not email:
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            with_csrf(
                request,
                error="Link expired or invalid. Request a new one.",
                sent=False,
            ),
        )

    session_token = create_session_token(email)
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=session_token,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        max_age=7 * 24 * 60 * 60,  # 7 days
    )
    return response


@router.post("/logout")
async def logout() -> RedirectResponse:
    """Clear the auth cookie and redirect to login."""
    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie(AUTH_COOKIE_NAME)
    return response
