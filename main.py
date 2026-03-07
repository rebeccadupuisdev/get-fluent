from contextlib import asynccontextmanager

import motor.motor_asyncio
from beanie import init_beanie
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "get_fluent"


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
    from models import DOCUMENT_MODELS

    await init_beanie(database=client[DB_NAME], document_models=DOCUMENT_MODELS)
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
