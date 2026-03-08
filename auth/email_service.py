"""Email delivery for magic links. Supports Resend, SMTP, or dev console fallback."""

import logging
import os
import smtplib
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

BODY_TEMPLATE = """Sign in to Get Fluent

Click the link below to sign in. This link expires in 15 minutes.

{magic_link_url}

If you didn't request this email, you can safely ignore it.
"""


def _send_via_resend(to_email: str, magic_link_url: str) -> bool:
    """Send via Resend API. Returns True on success."""
    import resend

    api_key = os.getenv("RESEND_API_KEY")
    from_addr = os.getenv(
        "RESEND_FROM",
        "Get Fluent <onboarding@resend.dev>",
    )

    resend.api_key = api_key
    body = BODY_TEMPLATE.format(magic_link_url=magic_link_url)

    try:
        resend.Emails.send({
            "from": from_addr,
            "to": [to_email],
            "subject": "Sign in to Get Fluent",
            "text": body,
        })
        return True
    except Exception as e:
        logger.exception("Resend failed to send magic link email: %s", e)
        return False


def _send_via_smtp(to_email: str, magic_link_url: str) -> bool:
    """Send via SMTP. Returns True on success."""
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    from_addr = os.getenv("SMTP_FROM", smtp_user or "noreply@localhost")
    body = BODY_TEMPLATE.format(magic_link_url=magic_link_url)

    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = "Sign in to Get Fluent"
        msg["From"] = from_addr
        msg["To"] = to_email

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(from_addr, [to_email], msg.as_string())
        return True
    except Exception as e:
        logger.exception("SMTP failed to send magic link email: %s", e)
        return False


def _dev_fallback(to_email: str, magic_link_url: str) -> bool:
    """Log magic link to console when no provider configured (dev only)."""
    is_dev = (
        os.getenv("DEBUG", "").lower() in ("true", "1", "yes")
        or os.getenv("ENV", "").lower() == "development"
    )
    if is_dev:
        logger.info(
            "No email provider configured. Magic link for %s: %s",
            to_email,
            magic_link_url,
        )
        print(f"\n--- Magic link for {to_email} ---\n{magic_link_url}\n---\n", flush=True)
        return True
    logger.warning(
        "No email provider configured; magic link not sent for %s. "
        "Set RESEND_API_KEY, SMTP_*, or DEBUG=true for dev.",
        to_email,
    )
    return True


def send_magic_link_email(to_email: str, magic_link_url: str) -> bool:
    """
    Send the magic link to the given email.
    Uses Resend if RESEND_API_KEY is set, else SMTP if configured, else dev console fallback.
    """
    if os.getenv("RESEND_API_KEY"):
        return _send_via_resend(to_email, magic_link_url)

    smtp_host = os.getenv("SMTP_HOST")
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    if smtp_host and smtp_user and smtp_password:
        return _send_via_smtp(to_email, magic_link_url)

    return _dev_fallback(to_email, magic_link_url)
