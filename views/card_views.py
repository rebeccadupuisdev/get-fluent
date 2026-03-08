from typing import Annotated

from fastapi import APIRouter, File, Form, Request, Response, UploadFile
from fastapi.responses import HTMLResponse

from services import audio_service, card_service, tag_service
from views.deps import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Render the main index page with all tags and cards."""
    all_tags = await tag_service.get_all_tags()
    valid_parent_tags = await tag_service.get_valid_parent_tags()
    cards = await card_service.get_cards()
    counts = await card_service.get_card_counts_by_tag()
    tag_tree = tag_service.build_tag_tree(all_tags, counts)
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "tag_tree": tag_tree,
            "tags": valid_parent_tags,
            "cards": cards,
            "total_cards": len(cards),
            "q": None,
            "tag_slug": None,
        },
    )


@router.post("/cards", response_class=HTMLResponse)
async def create_card(
    request: Request,
    phrase: Annotated[str, Form()],
    tag_slugs: Annotated[list[str], Form()] = [],
    audio: Annotated[UploadFile | None, File()] = None,
) -> HTMLResponse:
    """Create a new card and return the card item HTML fragment."""
    audio_filename: str | None = None
    if audio and audio.filename:
        audio_filename = await audio_service.save_audio(audio)

    card = await card_service.create_card(
        phrase=phrase,
        tag_slugs=tag_slugs,
        audio_filename=audio_filename,
    )
    cards = await card_service.get_cards()
    all_tags = await tag_service.get_all_tags()
    counts = await card_service.get_card_counts_by_tag()
    tag_tree = tag_service.build_tag_tree(all_tags, counts)
    return templates.TemplateResponse(
        request,
        "partials/card_list_with_tags.html",
        {
            "cards": cards,
            "q": None,
            "tag_slug": None,
            "tag_tree": tag_tree,
            "total_cards": len(cards),
        },
    )


@router.get("/cards", response_class=HTMLResponse)
async def list_cards(
    request: Request,
    tag_slug: str | None = None,
    q: str | None = None,
) -> HTMLResponse:
    """Return the card list HTML fragment, filtered by tag slug or search query."""
    if q:
        cards = await card_service.search_cards(q, tag_slug=tag_slug)
    else:
        cards = await card_service.get_cards(tag_slug=tag_slug)
    return templates.TemplateResponse(
        request,
        "partials/card_list.html",
        {"cards": cards, "q": q, "tag_slug": tag_slug},
    )


@router.put("/cards/{card_id}", response_class=HTMLResponse)
async def update_card(
    request: Request,
    card_id: str,
    phrase: Annotated[str, Form()],
    tag_slugs: Annotated[list[str], Form()] = [],
    audio: Annotated[UploadFile | None, File()] = None,
    remove_audio: Annotated[str, Form()] = "false",
) -> HTMLResponse:
    """Update a card's phrase, tags, and audio; return the refreshed card list."""
    existing = await card_service.get_card(card_id)
    current_audio = existing.audio_filename if existing else None

    if audio and audio.filename:
        new_filename = await audio_service.save_audio(audio)
        if current_audio:
            await audio_service.delete_audio(current_audio)
        audio_filename: str | None = new_filename
    elif remove_audio == "true":
        if current_audio:
            await audio_service.delete_audio(current_audio)
        audio_filename = None
    else:
        audio_filename = current_audio

    await card_service.update_card(
        card_id=card_id,
        phrase=phrase,
        tag_slugs=tag_slugs,
        audio_filename=audio_filename,
    )
    cards = await card_service.get_cards()
    all_tags = await tag_service.get_all_tags()
    counts = await card_service.get_card_counts_by_tag()
    tag_tree = tag_service.build_tag_tree(all_tags, counts)
    return templates.TemplateResponse(
        request,
        "partials/card_list_with_tags.html",
        {
            "cards": cards,
            "q": None,
            "tag_slug": None,
            "tag_tree": tag_tree,
            "total_cards": len(cards),
        },
    )


@router.delete("/cards/{card_id}", response_class=HTMLResponse)
async def delete_card(request: Request, card_id: str) -> HTMLResponse:
    """Delete a card and its associated audio, then return the updated card list."""
    audio_filename = await card_service.delete_card(card_id)
    if audio_filename:
        await audio_service.delete_audio(audio_filename)
    cards = await card_service.get_cards()
    all_tags = await tag_service.get_all_tags()
    counts = await card_service.get_card_counts_by_tag()
    tag_tree = tag_service.build_tag_tree(all_tags, counts)
    return templates.TemplateResponse(
        request,
        "partials/card_list_with_tags.html",
        {
            "cards": cards,
            "q": None,
            "tag_slug": None,
            "tag_tree": tag_tree,
            "total_cards": len(cards),
        },
    )
