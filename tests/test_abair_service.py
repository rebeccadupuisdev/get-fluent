import base64
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

import services.abair_service as abair_service


def _make_mock_client(response: MagicMock) -> tuple[MagicMock, MagicMock]:
    """Return (mock_cls, mock_inner_client) with async context manager wired up."""
    mock_inner = AsyncMock()
    mock_inner.get = AsyncMock(return_value=response)

    mock_cls = MagicMock()
    mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_inner)
    mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    return mock_cls, mock_inner


def _ok_response(audio_bytes: bytes) -> MagicMock:
    """Build a mock httpx response that returns base64-encoded audio."""
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"audioContent": base64.b64encode(audio_bytes).decode()}
    return resp


# ---------------------------------------------------------------------------
# Test 1 — happy path
# ---------------------------------------------------------------------------


async def test_synthesise_returns_decoded_audio_bytes():
    expected = b"fake wav audio data"
    mock_cls, _ = _make_mock_client(_ok_response(expected))

    with patch("httpx.AsyncClient", mock_cls):
        result = await abair_service.synthesise("Dia duit")

    assert result == expected


# ---------------------------------------------------------------------------
# Test 2 — error path: non-2xx response propagates HTTPStatusError
# ---------------------------------------------------------------------------


async def test_synthesise_propagates_http_status_error():
    resp = MagicMock()
    resp.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "500 Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        )
    )
    mock_cls, _ = _make_mock_client(resp)

    with patch("httpx.AsyncClient", mock_cls):
        with pytest.raises(httpx.HTTPStatusError):
            await abair_service.synthesise("Dia duit")


# ---------------------------------------------------------------------------
# Test 3 — correct query params are sent to ABAIR
# ---------------------------------------------------------------------------


async def test_synthesise_sends_correct_query_params():
    mock_cls, mock_inner = _make_mock_client(_ok_response(b"audio"))

    with patch("httpx.AsyncClient", mock_cls):
        await abair_service.synthesise("Dia duit")

    mock_inner.get.assert_awaited_once_with(
        abair_service.ABAIR_SYNTH_URL,
        params={
            "input": "Dia duit",
            "voice": abair_service.DEFAULT_VOICE,
            "normalise": "true",
        },
    )
