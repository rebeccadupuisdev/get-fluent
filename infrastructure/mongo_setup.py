import os

from beanie import init_beanie
from pymongo import AsyncMongoClient

from models.card import Card
from models.tag import Tag

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI or not MONGO_URI.strip():
    raise ValueError(
        "MONGO_URI must be set. Add it to .env (e.g. MONGO_URI=mongodb://localhost:27017)"
    )


async def init_connection(db_name: str):
    conn_str = f"{MONGO_URI.rstrip('/')}/{db_name}"
    client = AsyncMongoClient(conn_str)

    await init_beanie(database=client[db_name], document_models=[Card, Tag])

    return client
