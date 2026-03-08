"""Email delivery for magic links. When SMTP is not configured, logs link only if DEBUG or ENV=development."""

import logging
import os
import smtplib
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def send_magic_link_email(to_email: str, magic_link_url: str) -> bool:
    """
    Send the magic link to the given email.
    If SMTP is not configured, logs the link to console and returns True (for dev).
    """
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    from_addr = os.getenv("SMTP_FROM", smtp_user or "noreply@localhost")

    body = f"""Sign in to Get Fluent

Click the link below to sign in. This link expires in 15 minutes.

{magic_link_url}

If you didn't request this email, you can safely ignore it.
"""

    if not smtp_host or not smtp_user or not smtp_password:
        is_dev = (
            os.getenv("DEBUG", "").lower() in ("true", "1", "yes")
            or os.getenv("ENV", "").lower() == "development"
        )
        if is_dev:
            logger.info(
                "SMTP not configured. Magic link for %s: %s",
                to_email,
                magic_link_url,
            )
            print(f"\n--- Magic link for {to_email} ---\n{magic_link_url}\n---\n", flush=True)
        else:
            logger.warning(
                "SMTP not configured; magic link not sent for %s. Set SMTP_* or DEBUG=true for dev.",
                to_email,
            )
        return True

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
        logger.exception("Failed to send magic link email: %s", e)
        return False
