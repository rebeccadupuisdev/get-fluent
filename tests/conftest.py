import mongomock_motor
import pytest_asyncio
from beanie import init_beanie

from models.card import Card
from models.tag import Tag


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
