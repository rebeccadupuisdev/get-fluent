import os

from beanie import init_beanie
from pymongo import AsyncMongoClient

from models.card import Card
from models.tag import Tag

MONGO_URI = os.getenv("MONGO_URI")


async def init_connection(db_name: str):
    conn_str = f"{MONGO_URI}/{db_name}"
    client = AsyncMongoClient(conn_str)

    await init_beanie(database=client[db_name], document_models=[Card, Tag])

    return client
