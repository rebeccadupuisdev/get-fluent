from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from services import tag_service
from views.deps import templates

router = APIRouter()


@router.get("/tags", response_class=HTMLResponse)
async def list_tags(request: Request) -> HTMLResponse:
    """Return the tag tree HTML fragment."""
    tags = await tag_service.get_all_tags()
    tag_tree = tag_service.build_tag_tree(tags)
    return templates.TemplateResponse(
        request,
        "partials/tag_tree.html",
        {"tag_tree": tag_tree},
    )


@router.post("/tags", response_class=HTMLResponse)
async def create_tag(
    request: Request,
    name: Annotated[str, Form()],
    parent_slug: Annotated[str | None, Form()] = None,
) -> HTMLResponse:
    """Create a new tag and return the updated tag form with an OOB tag tree swap."""
    await tag_service.create_tag(name=name, parent_slug=parent_slug or None)
    tags = await tag_service.get_all_tags()
    tag_tree = tag_service.build_tag_tree(tags)
    return templates.TemplateResponse(
        request,
        "partials/tag_form.html",
        {"tags": tags, "tag_tree": tag_tree},
    )
