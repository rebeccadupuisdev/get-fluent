import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from infrastructure.mongo_setup import init_connection

DB_NAME = os.getenv("DB_NAME", "get_fluent")


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = await init_connection(DB_NAME)
    yield
    client.close()


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

templates = Jinja2Templates(directory="frontend/templates")

# Routers — included in Task 4.7
# from views.card_views import router as card_router
# from views.tag_views import router as tag_router
# app.include_router(card_router)
# app.include_router(tag_router)
