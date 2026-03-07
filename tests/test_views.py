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
    """Async HTTP client wired directly to the ASGI app, no lifespan."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
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
    with patch("services.audio_service.save_audio", new_callable=AsyncMock, return_value="saved.mp3"):
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


async def test_list_cards_q_takes_precedence_over_tag_slug(client):
    """When both q and tag_slug are supplied, q wins and tag_slug is ignored."""
    await client.post("/tags", data={"name": "French"})
    await client.post("/cards", data={"phrase": "Bonjour", "tag_slugs": "french"})
    await client.post("/cards", data={"phrase": "Hola"})

    response = await client.get("/cards", params={"q": "hola", "tag_slug": "french"})

    assert response.status_code == 200
    assert "Hola" in response.text
    assert "Bonjour" not in response.text


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
    response = await client.post("/tags", data={"name": "French", "parent_slug": "nonexistent"})

    assert response.status_code == 200
    assert "does not exist" in response.text


async def test_create_tag_too_deep_returns_error(client):
    await client.post("/tags", data={"name": "Language"})
    await client.post("/tags", data={"name": "Spanish", "parent_slug": "language"})
    await client.post("/tags", data={"name": "Mexican Spanish", "parent_slug": "spanish"})

    response = await client.post("/tags", data={"name": "CDMX Spanish", "parent_slug": "mexican-spanish"})

    assert response.status_code == 200
    assert "two levels" in response.text


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
