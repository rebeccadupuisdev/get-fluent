from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from pydantic import ValidationError

from auth.deps import require_auth
from services import card_service, tag_service
from views.deps import templates


router = APIRouter()


@router.get("/tags", response_class=HTMLResponse)
async def list_tags(request: Request) -> HTMLResponse:
    """Return the tag tree HTML fragment."""
    tags = await tag_service.get_all_tags()
    counts = await card_service.get_card_counts_by_tag()
    tag_tree = tag_service.build_tag_tree(tags, counts)
    return templates.TemplateResponse(
        request,
        "partials/tag_tree.html",
        {"tag_tree": tag_tree},
    )


@router.delete("/tags/empty", response_class=HTMLResponse)
async def delete_empty_tags(
    request: Request,
    _email: Annotated[str, Depends(require_auth)],
) -> HTMLResponse:
    """Delete all tags not attached to any card; return refreshed tag tree and modal form."""
    await tag_service.delete_empty_tags()
    all_tags = await tag_service.get_all_tags()
    valid_parent_tags = await tag_service.get_valid_parent_tags()
    counts = await card_service.get_card_counts_by_tag()
    tag_tree = tag_service.build_tag_tree(all_tags, counts)
    return templates.TemplateResponse(
        request,
        "partials/tag_form.html",
        {"tags": valid_parent_tags, "tag_tree": tag_tree},
    )


@router.post("/tags", response_class=HTMLResponse)
async def create_tag(
    request: Request,
    _email: Annotated[str, Depends(require_auth)],
    name: Annotated[str, Form()],
    parent_slug: Annotated[str | None, Form()] = None,
) -> HTMLResponse:
    """Create a new tag; return OOB tag tree update and refreshed modal form."""
    try:
        await tag_service.create_tag(name=name, parent_slug=parent_slug or None)
    except ValueError as exc:
        all_tags = await tag_service.get_all_tags()
        valid_parent_tags = await tag_service.get_valid_parent_tags()
        counts = await card_service.get_card_counts_by_tag()
        tag_tree = tag_service.build_tag_tree(all_tags, counts)
        return templates.TemplateResponse(
            request,
            "partials/tag_form.html",
            {"tags": valid_parent_tags, "tag_tree": tag_tree, "error": str(exc)},
        )
    except ValidationError:
        all_tags = await tag_service.get_all_tags()
        valid_parent_tags = await tag_service.get_valid_parent_tags()
        counts = await card_service.get_card_counts_by_tag()
        tag_tree = tag_service.build_tag_tree(all_tags, counts)
        return templates.TemplateResponse(
            request,
            "partials/tag_form.html",
            {"tags": valid_parent_tags, "tag_tree": tag_tree, "error": "Tag name too long (max 100 characters)"},
        )
    all_tags = await tag_service.get_all_tags()
    valid_parent_tags = await tag_service.get_valid_parent_tags()
    counts = await card_service.get_card_counts_by_tag()
    tag_tree = tag_service.build_tag_tree(all_tags, counts)
    return templates.TemplateResponse(
        request,
        "partials/tag_form.html",
        {"tags": valid_parent_tags, "tag_tree": tag_tree},
    )
