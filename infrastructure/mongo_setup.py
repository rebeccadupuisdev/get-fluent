import os

from beanie import init_beanie
from motor import motor_asyncio

from models.card import Card
from models.tag import Tag

MONGO_URI = os.getenv("MONGO_URI")


async def init_connection(db_name: str):
    conn_str = f"{MONGO_URI}/{db_name}"
    client = motor_asyncio.AsyncIOMotorClient(conn_str)

    await init_beanie(database=client[db_name], document_models=[Card, Tag])

    return client
