"""Unit tests for `auth.email_service` provider branching and SMTP/Resend wrappers."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from auth.email_service import send_magic_link_email


@pytest.fixture(autouse=True)
def isolate_email_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent host env SMTP/Resend/Debug from affecting provider selection."""
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    monkeypatch.delenv("DEBUG", raising=False)
    monkeypatch.delenv("ENV", raising=False)


def test_send_magic_link_via_resend_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RESEND_API_KEY", "re_fake_key")

    with patch("resend.Emails.send") as mock_send:
        mock_send.return_value = {"id": "msg-abc"}
        result = send_magic_link_email(
            "user@example.com", "http://localhost/auth/verify?token=x"
        )

    assert result is True
    mock_send.assert_called_once()


def test_send_magic_link_via_resend_failure_returns_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RESEND_API_KEY", "re_fake_key")

    with patch("resend.Emails.send", side_effect=RuntimeError("upstream error")):
        result = send_magic_link_email(
            "user@example.com", "http://localhost/auth/verify?token=x"
        )

    assert result is False


def test_send_magic_link_prefers_resend_when_smtp_also_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RESEND_API_KEY", "re_key")
    monkeypatch.setenv("SMTP_HOST", "mail.example.org")
    monkeypatch.setenv("SMTP_USER", "u")
    monkeypatch.setenv("SMTP_PASSWORD", "p")

    with patch("resend.Emails.send", return_value={"id": "1"}) as mock_send:
        with patch("auth.email_service.smtplib.SMTP") as mock_smtp:
            assert send_magic_link_email("x@example.com", "http://magic") is True

    mock_send.assert_called_once()
    mock_smtp.assert_not_called()


def test_send_magic_link_via_smtp_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMTP_HOST", "localhost")
    monkeypatch.setenv("SMTP_USER", "u")
    monkeypatch.setenv("SMTP_PASSWORD", "p")

    smtp_inst = MagicMock()
    smtp_inst.__enter__ = MagicMock(return_value=smtp_inst)
    smtp_inst.__exit__ = MagicMock(return_value=False)

    with patch("auth.email_service.smtplib.SMTP", return_value=smtp_inst):
        assert send_magic_link_email("who@example.com", "http://link") is True

    smtp_inst.starttls.assert_called_once()
    smtp_inst.login.assert_called_once_with("u", "p")
    smtp_inst.sendmail.assert_called_once()


def test_send_magic_link_via_smtp_failure_returns_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SMTP_HOST", "localhost")
    monkeypatch.setenv("SMTP_USER", "u")
    monkeypatch.setenv("SMTP_PASSWORD", "p")

    smtp_inst = MagicMock()
    smtp_inst.__enter__ = MagicMock(return_value=smtp_inst)
    smtp_inst.__exit__ = MagicMock(return_value=False)
    smtp_inst.starttls.side_effect = OSError("cannot reach host")

    with patch("auth.email_service.smtplib.SMTP", return_value=smtp_inst):
        result = send_magic_link_email("who@example.com", "http://link")

    assert result is False


def test_send_magic_link_dev_fallback_true_when_debug_enabled(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("DEBUG", "true")

    with caplog.at_level(logging.INFO, logger="auth.email_service"):
        result = send_magic_link_email(
            "dev@example.com", "http://localhost/auth/verify?token=z"
        )

    assert result is True
    assert any(
        "No email provider configured" in r.message and "Magic link" in r.message
        for r in caplog.records
    )


def test_send_magic_link_dev_fallback_logs_warning_when_no_provider_prodish(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger="auth.email_service"):
        result = send_magic_link_email(
            "nouser@example.com", "http://localhost/auth/verify?token=y"
        )

    assert result is True
    assert any(
        "No email provider configured" in r.message for r in caplog.records
    )
