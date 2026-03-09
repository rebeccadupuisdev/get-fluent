import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from auth.limiter import limiter
from auth.views import router as auth_router
from infrastructure.mongo_setup import init_connection
from middleware.csrf import CSRFMiddleware
from views.card_views import router as card_router
from views.tag_views import router as tag_router

DB_NAME = os.getenv("DB_NAME", "get_fluent")


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = await init_connection(DB_NAME)
    yield
    await client.close()


app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(CSRFMiddleware)

app.mount("/static", StaticFiles(directory="frontend/static"), name="static")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return RedirectResponse(url="/static/favicons/favicon.ico")


app.include_router(auth_router)
app.include_router(card_router)
app.include_router(tag_router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Redirect to login on 401; HTMX requests get HX-Redirect header."""
    if exc.status_code == 401:
        if request.headers.get("HX-Request"):
            return JSONResponse(
                status_code=401,
                content={"detail": exc.detail},
                headers={"HX-Redirect": "/auth/login"},
            )
        return RedirectResponse(url="/auth/login", status_code=302)
    # Default: let FastAPI handle other HTTPExceptions
    from fastapi.exception_handlers import http_exception_handler as default

    return await default(request, exc)
