import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from infrastructure.mongo_setup import init_connection
from views.card_views import router as card_router
from views.tag_views import router as tag_router

DB_NAME = os.getenv("DB_NAME", "get_fluent")


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = await init_connection(DB_NAME)
    yield
    await client.close()


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

app.include_router(card_router)
app.include_router(tag_router)
