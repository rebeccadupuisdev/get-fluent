import hashlib
from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="frontend/templates")


def _file_hash(path: str, length: int = 8) -> str:
    """Return a short hex digest of a file's contents, for cache-busting."""
    try:
        return hashlib.md5(Path(path).read_bytes()).hexdigest()[:length]
    except OSError:
        return "0"


templates.env.globals["static_js_hash"] = _file_hash("frontend/static/js/main.js")


def with_csrf(request: Request, **context) -> dict:
    """Merge context with csrf_token for templates that need it."""
    token = getattr(request.state, "csrf_token", "")
    return {**context, "csrf_token": token}
