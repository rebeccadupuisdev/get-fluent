import os

import mongomock_motor
import pytest_asyncio
from beanie import init_beanie

from models.card import Card
from models.tag import Tag

# Auth env for tests — must be set before importing auth module
os.environ.setdefault("AUTH_SECRET", "test-secret-do-not-use-in-production")
os.environ.setdefault("AUTH_EMAIL_WHITELIST", "test@example.com")


@pytest_asyncio.fixture(autouse=True)
async def beanie_init():
    """Spin up a fresh in-memory Beanie instance for each test."""
    client = mongomock_motor.AsyncMongoMockClient()
    await init_beanie(
        database=client.get_database("test_db"),
        document_models=[Tag, Card],
    )
    yield
    await Tag.find_all().delete()
    await Card.find_all().delete()


@pytest_asyncio.fixture(autouse=True)
async def auth_override():
    """Override auth for tests: bypass requires a valid session cookie."""
    from main import app
    from auth.deps import require_auth

    async def mock_require_auth():
        return "test@example.com"

    app.dependency_overrides[require_auth] = mock_require_auth
    yield
    app.dependency_overrides.pop(require_auth, None)
