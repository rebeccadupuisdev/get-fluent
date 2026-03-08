from fastapi import Request
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="frontend/templates")


def with_csrf(request: Request, **context) -> dict:
    """Merge context with csrf_token for templates that need it."""
    token = getattr(request.state, "csrf_token", "")
    return {**context, "csrf_token": token}
