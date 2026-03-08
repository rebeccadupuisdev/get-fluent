"""Smoke tests for view route handlers.

Uses httpx.AsyncClient with ASGITransport so the ASGI lifespan (which
would try to reach a real MongoDB) is never triggered.  The autouse
beanie_init fixture in conftest.py has already initialised Beanie
against a mongomock_motor client before each test function runs.
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest_asyncio

from main import app
from models.card import Card


@pytest_asyncio.fixture
async def client():
    """Async HTTP client wired directly to the ASGI app, no lifespan.
    Establishes CSRF cookie via GET, then adds X-CSRF-Token header for state-changing requests.
    """
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        r = await ac.get("/")
        r.raise_for_status()
        csrf_cookie = ac.cookies.get("csrftoken")
        if csrf_cookie:
            ac.headers["X-CSRF-Token"] = csrf_cookie
        yield ac


async def test_index_returns_200(client):
    response = await client.get("/")
    assert response.status_code == 200


async def test_create_card_returns_fragment(client):
    response = await client.post("/cards", data={"phrase": "Bonjour"})
    assert response.status_code == 200
    assert "Bonjour" in response.text


async def test_create_card_without_tags(client):
    response = await client.post("/cards", data={"phrase": "Au revoir"})
    assert response.status_code == 200


async def test_create_card_phrase_too_long_returns_422(client):
    """Phrase exceeding 2000 chars returns 422 (input length limit)."""
    response = await client.post("/cards", data={"phrase": "x" * 2001})
    assert response.status_code == 422


async def test_create_card_empty_phrase_returns_422(client):
    """Empty phrase returns 422 (FastAPI Form validation)."""
    response = await client.post("/cards", data={"phrase": ""})

    assert response.status_code == 422


async def test_create_card_whitespace_only_phrase_returns_422(client):
    """Whitespace-only phrase returns 422 (treated as empty)."""
    response = await client.post("/cards", data={"phrase": "   "})

    assert response.status_code == 422


async def test_create_card_phrase_exactly_2000_chars_succeeds(client):
    """Phrase at exactly 2000 chars (boundary) is accepted."""
    response = await client.post("/cards", data={"phrase": "x" * 2000})
    assert response.status_code == 200
    assert "x" * 2000 in response.text


async def test_list_cards_returns_fragment(client):
    response = await client.get("/cards")
    assert response.status_code == 200


async def test_list_cards_with_query_returns_matching_card(client):
    await client.post("/cards", data={"phrase": "Hola mundo"})
    await client.post("/cards", data={"phrase": "Bonjour monde"})

    response = await client.get("/cards", params={"q": "hola"})

    assert response.status_code == 200
    assert "Hola mundo" in response.text
    assert "Bonjour monde" not in response.text


async def test_list_cards_with_tag_slug_returns_filtered_cards(client):
    await client.post("/tags", data={"name": "French"})
    await client.post("/cards", data={"phrase": "Bonjour", "tag_slugs": "french"})
    await client.post("/cards", data={"phrase": "Hello"})

    response = await client.get("/cards", params={"tag_slug": "french"})

    assert response.status_code == 200
    assert "Bonjour" in response.text
    assert "Hello" not in response.text


async def test_delete_card_returns_200(client):
    await client.post("/cards", data={"phrase": "À bientôt"})
    card = await Card.find_one()
    assert card is not None

    response = await client.delete(f"/cards/{card.id}")

    assert response.status_code == 200
    assert await Card.find_one(Card.id == card.id) is None


async def test_delete_nonexistent_card_returns_200(client):
    """DELETE is idempotent — a missing card still yields a 200."""
    from bson import ObjectId

    fake_id = str(ObjectId())
    response = await client.delete(f"/cards/{fake_id}")
    assert response.status_code == 200


async def test_delete_card_malformed_id_returns_200(client):
    """A non-ObjectId card ID does not raise a 500."""
    response = await client.delete("/cards/not-a-valid-object-id")
    assert response.status_code == 200


async def test_create_card_with_audio_upload(client):
    """Audio file upload is saved and the filename is stored on the card."""
    with patch(
        "services.audio_service.save_audio",
        new_callable=AsyncMock,
        return_value="saved.mp3",
    ):
        response = await client.post(
            "/cards",
            data={"phrase": "Bonsoir"},
            files={"audio": ("clip.mp3", b"fake audio bytes", "audio/mpeg")},
        )

    assert response.status_code == 200
    assert "Bonsoir" in response.text

    card = await Card.find_one()
    assert card is not None
    assert card.audio_filename == "saved.mp3"


async def test_list_cards_q_and_tag_slug_both_apply(client):
    """When both q and tag_slug are supplied, both filters are applied (AND logic)."""
    await client.post("/tags", data={"name": "French"})
    await client.post("/cards", data={"phrase": "Bonjour", "tag_slugs": "french"})
    await client.post("/cards", data={"phrase": "Buen día", "tag_slugs": "spanish"})

    response = await client.get("/cards", params={"q": "b", "tag_slug": "french"})

    assert response.status_code == 200
    assert "Bonjour" in response.text
    assert "Buen día" not in response.text


async def test_get_tags_empty_returns_200(client):
    response = await client.get("/tags")
    assert response.status_code == 200


async def test_get_tags_returns_fragment(client):
    await client.post("/tags", data={"name": "Spanish"})

    response = await client.get("/tags")

    assert response.status_code == 200
    assert "Spanish" in response.text


async def test_create_tag_returns_form_fragment(client):
    response = await client.post("/tags", data={"name": "German"})
    assert response.status_code == 200
    assert "German" in response.text


async def test_create_tag_with_parent_returns_fragment(client):
    await client.post("/tags", data={"name": "Romance"})
    response = await client.post(
        "/tags", data={"name": "French", "parent_slug": "romance"}
    )
    assert response.status_code == 200
    assert "French" in response.text


async def test_create_tag_duplicate_returns_error_message(client):
    await client.post("/tags", data={"name": "Spanish"})

    response = await client.post("/tags", data={"name": "Spanish"})

    assert response.status_code == 200
    assert "already exists" in response.text


async def test_create_tag_nonexistent_parent_returns_error(client):
    response = await client.post(
        "/tags", data={"name": "French", "parent_slug": "nonexistent"}
    )

    assert response.status_code == 200
    assert "does not exist" in response.text


async def test_create_tag_too_deep_returns_error(client):
    await client.post("/tags", data={"name": "Language"})
    await client.post("/tags", data={"name": "Spanish", "parent_slug": "language"})
    await client.post(
        "/tags", data={"name": "Mexican Spanish", "parent_slug": "spanish"}
    )

    response = await client.post(
        "/tags", data={"name": "CDMX Spanish", "parent_slug": "mexican-spanish"}
    )

    assert response.status_code == 200
    assert "two levels" in response.text


async def test_create_tag_empty_name_returns_422(client):
    """Empty tag name returns 422 (FastAPI Form validation)."""
    response = await client.post("/tags", data={"name": ""})

    assert response.status_code == 422


async def test_create_tag_whitespace_only_name_returns_error_message(client):
    """Whitespace-only tag name returns form with error message."""
    response = await client.post("/tags", data={"name": "   "})

    assert response.status_code == 200
    assert "empty" in response.text.lower()


async def test_delete_empty_tags_no_tags_returns_200(client):
    """DELETE /tags/empty with no tags returns 200 (idempotent)."""
    response = await client.delete("/tags/empty")
    assert response.status_code == 200


async def test_delete_empty_tags_returns_200(client):
    await client.post("/tags", data={"name": "Unused"})

    response = await client.delete("/tags/empty")

    assert response.status_code == 200


async def test_delete_empty_tags_removes_unused_tag(client):
    await client.post("/tags", data={"name": "Unused"})

    await client.delete("/tags/empty")

    response = await client.get("/tags")
    assert "Unused" not in response.text


async def test_delete_empty_tags_keeps_used_tag(client):
    await client.post("/tags", data={"name": "Spanish"})
    await client.post("/cards", data={"phrase": "Hola", "tag_slugs": "spanish"})

    await client.delete("/tags/empty")

    response = await client.get("/tags")
    assert "Spanish" in response.text


# ---------------------------------------------------------------------------
# PUT /cards/{card_id}
# ---------------------------------------------------------------------------


async def test_update_card_returns_200(client):
    await client.post("/cards", data={"phrase": "Salut"})
    card = await Card.find_one()

    response = await client.put(f"/cards/{card.id}", data={"phrase": "Allo"})

    assert response.status_code == 200


async def test_update_card_phrase_appears_in_response(client):
    await client.post("/cards", data={"phrase": "Salut"})
    card = await Card.find_one()

    response = await client.put(f"/cards/{card.id}", data={"phrase": "Allo"})

    assert "Allo" in response.text


async def test_update_card_persists_new_phrase(client):
    await client.post("/cards", data={"phrase": "Salut"})
    card = await Card.find_one()

    await client.put(f"/cards/{card.id}", data={"phrase": "Allo"})

    refreshed = await Card.get(card.id)
    assert refreshed.phrase == "Allo"


async def test_update_card_with_tag_slug(client):
    await client.post("/tags", data={"name": "French"})
    await client.post("/cards", data={"phrase": "Bonjour"})
    card = await Card.find_one()

    response = await client.put(
        f"/cards/{card.id}", data={"phrase": "Bonjour", "tag_slugs": "french"}
    )

    assert response.status_code == 200
    refreshed = await Card.get(card.id)
    assert "french" in refreshed.tag_slugs


async def test_update_card_remove_audio(client):
    with patch(
        "services.audio_service.save_audio",
        new_callable=AsyncMock,
        return_value="clip.mp3",
    ):
        with patch("services.audio_service.delete_audio", new_callable=AsyncMock):
            await client.post(
                "/cards",
                data={"phrase": "Test"},
                files={"audio": ("clip.mp3", b"bytes", "audio/mpeg")},
            )

    card = await Card.find_one()
    assert card.audio_filename == "clip.mp3"

    with patch(
        "services.audio_service.delete_audio", new_callable=AsyncMock
    ) as mock_del:
        response = await client.put(
            f"/cards/{card.id}", data={"phrase": "Test", "remove_audio": "true"}
        )

    assert response.status_code == 200
    mock_del.assert_awaited_once_with("clip.mp3")
    refreshed = await Card.get(card.id)
    assert refreshed.audio_filename is None


async def test_update_card_upload_new_audio(client):
    await client.post("/cards", data={"phrase": "Test"})
    card = await Card.find_one()

    with patch(
        "services.audio_service.save_audio",
        new_callable=AsyncMock,
        return_value="new.mp3",
    ):
        response = await client.put(
            f"/cards/{card.id}",
            data={"phrase": "Test"},
            files={"audio": ("new.mp3", b"bytes", "audio/mpeg")},
        )

    assert response.status_code == 200
    refreshed = await Card.get(card.id)
    assert refreshed.audio_filename == "new.mp3"


async def test_update_card_nonexistent_id_returns_200(client):
    """Updating a missing card is handled gracefully — still returns the card list fragment."""
    from bson import ObjectId

    response = await client.put(f"/cards/{ObjectId()}", data={"phrase": "X"})

    assert response.status_code == 200


async def test_update_card_malformed_id_returns_200(client):
    response = await client.put("/cards/not-a-valid-id", data={"phrase": "X"})

    assert response.status_code == 200


async def test_update_card_phrase_too_long_returns_422(client):
    """Phrase exceeding 2000 chars on update returns 422 (input length limit)."""
    await client.post("/cards", data={"phrase": "Short"})
    card = await Card.find_one()

    response = await client.put(f"/cards/{card.id}", data={"phrase": "x" * 2001})

    assert response.status_code == 422


async def test_update_card_whitespace_only_phrase_returns_422(client):
    """Whitespace-only phrase on update returns 422 (treated as empty)."""
    await client.post("/cards", data={"phrase": "Short"})
    card = await Card.find_one()

    response = await client.put(f"/cards/{card.id}", data={"phrase": "   "})

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Auth — unauthenticated requests to protected routes
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client_no_auth():
    """Client without auth override — for testing 401 on protected routes."""
    from auth.deps import require_auth
    from main import app

    async def mock_require_auth():
        return "test@example.com"

    app.dependency_overrides.pop(require_auth, None)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            r = await ac.get("/")
            r.raise_for_status()
            csrf_cookie = ac.cookies.get("csrftoken")
            if csrf_cookie:
                ac.headers["X-CSRF-Token"] = csrf_cookie
            yield ac
    finally:
        app.dependency_overrides[require_auth] = mock_require_auth


async def test_create_card_unauthorized_returns_401(client_no_auth):
    """POST /cards without auth returns 401."""
    response = await client_no_auth.post(
        "/cards",
        data={"phrase": "Bonjour"},
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 401
    assert response.headers.get("HX-Redirect") == "/auth/login"


async def test_create_card_unauthorized_non_htmx_redirects_to_login(client_no_auth):
    """POST /cards without auth and without HX-Request returns 302 redirect to login."""
    response = await client_no_auth.post(
        "/cards",
        data={"phrase": "Bonjour"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"] == "/auth/login"


async def test_delete_card_unauthorized_returns_401(client_no_auth):
    """DELETE /cards/{id} without auth returns 401."""
    from bson import ObjectId

    response = await client_no_auth.delete(
        f"/cards/{ObjectId()}",
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 401


async def test_create_tag_unauthorized_returns_401(client_no_auth):
    """POST /tags without auth returns 401."""
    response = await client_no_auth.post(
        "/tags",
        data={"name": "German"},
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 401


async def test_delete_empty_tags_unauthorized_returns_401(client_no_auth):
    """DELETE /tags/empty without auth returns 401."""
    response = await client_no_auth.delete(
        "/tags/empty",
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 401


async def test_post_without_csrf_token_returns_403():
    """POST without X-CSRF-Token header returns 403 (CSRF protection)."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        response = await ac.post("/cards", data={"phrase": "Test"})
    assert response.status_code == 403


async def test_post_with_invalid_csrf_token_returns_403(client):
    """POST with mismatched X-CSRF-Token returns 403 (CSRF validation)."""
    client.headers["X-CSRF-Token"] = "wrong-token-value"
    response = await client.post("/cards", data={"phrase": "Test"})
    assert response.status_code == 403


async def test_post_with_csrf_token_in_form_succeeds():
    """POST with csrf_token in form body (no header) succeeds when token matches cookie."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        r = await ac.get("/")
        r.raise_for_status()
        csrf_cookie = ac.cookies.get("csrftoken")
        assert csrf_cookie is not None

        response = await ac.post(
            "/tags",
            data={"name": "Form CSRF tag", "csrf_token": csrf_cookie},
        )

    assert response.status_code == 200
    assert "Form CSRF tag" in response.text


async def test_logout_clears_cookie_and_redirects_to_login(client):
    """POST /auth/logout clears auth cookie and redirects to login page."""
    response = await client.post("/auth/logout")

    assert response.status_code == 302
    assert response.headers["location"] == "/auth/login"
    # Starlette delete_cookie sets Set-Cookie with empty value to expire the cookie
    set_cookie = response.headers.get("set-cookie", "").lower()
    assert "auth_token" in set_cookie


async def test_verify_valid_token_redirects_and_sets_cookie():
    """GET /auth/verify with valid token redirects to / and sets session cookie."""
    from auth.security import create_magic_link_token

    token = create_magic_link_token("test@example.com")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=False,
    ) as ac:
        response = await ac.get(f"/auth/verify?token={token}")

    assert response.status_code == 302
    assert response.headers["location"] == "/"
    set_cookie = response.headers.get("set-cookie", "").lower()
    assert "auth_token" in set_cookie


async def test_verify_missing_token_redirects_to_login():
    """GET /auth/verify without token redirects to login."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=False,
    ) as ac:
        response = await ac.get("/auth/verify")

    assert response.status_code == 302
    assert response.headers["location"] == "/auth/login"


async def test_login_page_returns_200():
    """GET /auth/login renders the login form."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        response = await ac.get("/auth/login")
    assert response.status_code == 200
    assert "magic link" in response.text.lower() or "sign in" in response.text.lower()


async def test_verify_invalid_token_shows_error():
    """GET /auth/verify with invalid token shows error message."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        response = await ac.get("/auth/verify?token=invalid-token")
    assert response.status_code == 200
    assert "expired" in response.text.lower() or "invalid" in response.text.lower()


async def test_verify_rate_limited():
    """GET /auth/verify returns 429 after 10 requests per minute."""
    from auth.limiter import limiter
    from auth.security import create_magic_link_token

    limiter.reset()
    token = create_magic_link_token("test@example.com")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=False,
    ) as ac:
        for _ in range(10):
            resp = await ac.get(f"/auth/verify?token={token}")
            assert resp.status_code == 302
        resp = await ac.get(f"/auth/verify?token={token}")

    assert resp.status_code == 429


async def test_request_magic_link_whitelisted_returns_sent():
    """POST /auth/request-magic-link with whitelisted email returns success UI."""
    with patch("auth.views.send_magic_link_email", return_value=True):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            r = await ac.get("/auth/login")
            r.raise_for_status()
            csrf = ac.cookies.get("csrftoken")
            if csrf:
                ac.headers["X-CSRF-Token"] = csrf
            response = await ac.post(
                "/auth/request-magic-link",
                data={"email": "test@example.com"},
            )

    assert response.status_code == 200
    assert "check your email" in response.text.lower()


async def test_request_magic_link_non_whitelisted_returns_same_ui():
    """Non-whitelisted email returns same success UI — no user enumeration."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        r = await ac.get("/auth/login")
        r.raise_for_status()
        csrf = ac.cookies.get("csrftoken")
        if csrf:
            ac.headers["X-CSRF-Token"] = csrf
        response = await ac.post(
            "/auth/request-magic-link",
            data={"email": "unknown@example.com"},
        )

    assert response.status_code == 200
    assert "check your email" in response.text.lower()


async def test_request_magic_link_email_send_failure_shows_error():
    """When send_magic_link_email returns False, error message is shown."""
    with patch("auth.views.send_magic_link_email", return_value=False):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            r = await ac.get("/auth/login")
            r.raise_for_status()
            csrf = ac.cookies.get("csrftoken")
            if csrf:
                ac.headers["X-CSRF-Token"] = csrf
            response = await ac.post(
                "/auth/request-magic-link",
                data={"email": "test@example.com"},
            )

    assert response.status_code == 200
    assert "failed to send email" in response.text.lower()


async def test_request_magic_link_rate_limited():
    """POST /auth/request-magic-link returns 429 after 5 requests per minute."""
    from auth.limiter import limiter

    limiter.reset()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        r = await ac.get("/auth/login")
        r.raise_for_status()
        csrf = ac.cookies.get("csrftoken")
        if csrf:
            ac.headers["X-CSRF-Token"] = csrf
        for _ in range(5):
            resp = await ac.post(
                "/auth/request-magic-link",
                data={"email": "test@example.com"},
            )
            assert resp.status_code == 200
        resp = await ac.post(
            "/auth/request-magic-link",
            data={"email": "test@example.com"},
        )
    assert resp.status_code == 429
