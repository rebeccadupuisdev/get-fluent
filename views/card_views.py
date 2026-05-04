from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import ValidationError

from auth.deps import get_optional_auth, require_auth
from services import abair_service, audio_service, card_service, tag_service
from views.deps import templates, with_csrf

router = APIRouter()


def _normalize_filter_str(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


async def _cards_for_view(q: str | None, tag_slug: str | None):
    """Same filtering rules as GET /cards (search + optional tag)."""
    qn = _normalize_filter_str(q)
    tag_n = _normalize_filter_str(tag_slug)
    if qn:
        return await card_service.search_cards(qn, tag_slug=tag_n)
    return await card_service.get_cards(tag_slug=tag_n)


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Render the main index page with all tags and cards."""
    all_tags = await tag_service.get_all_tags()
    valid_parent_tags = await tag_service.get_valid_parent_tags()
    cards = await card_service.get_cards()
    counts = await card_service.get_card_counts_by_tag()
    tag_tree = tag_service.build_tag_tree(all_tags, counts)
    user_email = get_optional_auth(request)
    return templates.TemplateResponse(
        request,
        "index.html",
        with_csrf(
            request,
            tag_tree=tag_tree,
            tags=valid_parent_tags,
            cards=cards,
            total_cards=len(cards),
            q=None,
            tag_slug=None,
            user_email=user_email,
        ),
    )


@router.post("/cards/synthesise", response_class=JSONResponse)
async def synthesise_card_audio(
    _email: Annotated[str, Depends(require_auth)],
    phrase: Annotated[str, Form()],
) -> JSONResponse:
    """Synthesise Irish TTS audio for the given phrase via ABAIR and save to disk."""
    if not phrase.strip():
        raise HTTPException(422, "Phrase must not be empty.")
    try:
        audio_bytes = await abair_service.synthesise(phrase.strip())
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, f"ABAIR returned {exc.response.status_code}")
    except Exception:
        raise HTTPException(502, "Audio synthesis failed")
    filename = await audio_service.save_audio_bytes(audio_bytes, ".wav")
    return JSONResponse({"filename": filename})


@router.post("/cards", response_class=HTMLResponse)
async def create_card(
    request: Request,
    _email: Annotated[str, Depends(require_auth)],
    phrase: Annotated[str, Form()],
    translation: Annotated[str, Form()] = "",
    tag_slugs: Annotated[list[str], Form()] = [],
    audio: Annotated[UploadFile | None, File()] = None,
    synthesised_audio_filename: Annotated[str, Form()] = "",
) -> HTMLResponse:
    """Create a new card and return the card item HTML fragment."""
    audio_filename: str | None = None
    if audio and audio.filename:
        audio_filename = await audio_service.save_audio(audio)
    elif synthesised_audio_filename:
        audio_filename = synthesised_audio_filename

    try:
        card = await card_service.create_card(
            phrase=phrase,
            tag_slugs=tag_slugs,
            audio_filename=audio_filename,
            translation=translation.strip() or None,
        )
    except ValidationError:
        raise HTTPException(422, "Phrase too long (max 2000 characters)")
    except ValueError as exc:
        raise HTTPException(422, str(exc))

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
            "user_email": _email,
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
    user_email = get_optional_auth(request)
    return templates.TemplateResponse(
        request,
        "partials/card_list.html",
        {"cards": cards, "q": q, "tag_slug": tag_slug, "user_email": user_email},
    )


@router.put("/cards/{card_id}", response_class=HTMLResponse)
async def update_card(
    request: Request,
    _email: Annotated[str, Depends(require_auth)],
    card_id: str,
    phrase: Annotated[str, Form()],
    translation: Annotated[str, Form()] = "",
    tag_slugs: Annotated[list[str], Form()] = [],
    audio: Annotated[UploadFile | None, File()] = None,
    remove_audio: Annotated[str, Form()] = "false",
    synthesised_audio_filename: Annotated[str, Form()] = "",
    q: Annotated[str | None, Form()] = None,
    tag_slug: Annotated[str | None, Form()] = None,
) -> HTMLResponse:
    """Update a card's phrase, tags, and audio; return the refreshed card list."""
    existing = await card_service.get_card(card_id)
    current_audio = existing.audio_filename if existing else None

    if audio and audio.filename:
        new_filename = await audio_service.save_audio(audio)
        if current_audio:
            await audio_service.delete_audio(current_audio)
        audio_filename: str | None = new_filename
    elif synthesised_audio_filename:
        if current_audio:
            await audio_service.delete_audio(current_audio)
        audio_filename = synthesised_audio_filename
    elif remove_audio == "true":
        if current_audio:
            await audio_service.delete_audio(current_audio)
        audio_filename = None
    else:
        audio_filename = current_audio

    try:
        await card_service.update_card(
            card_id=card_id,
            phrase=phrase,
            tag_slugs=tag_slugs,
            audio_filename=audio_filename,
            translation=translation.strip() or None,
        )
    except ValidationError:
        raise HTTPException(422, "Phrase too long (max 2000 characters)")
    except ValueError as exc:
        raise HTTPException(422, str(exc))

    cards = await _cards_for_view(q, tag_slug)
    total_cards = len(await card_service.get_cards())
    all_tags = await tag_service.get_all_tags()
    counts = await card_service.get_card_counts_by_tag()
    tag_tree = tag_service.build_tag_tree(all_tags, counts)
    q_ctx = _normalize_filter_str(q)
    tag_ctx = _normalize_filter_str(tag_slug)
    return templates.TemplateResponse(
        request,
        "partials/card_list_with_tags.html",
        {
            "cards": cards,
            "q": q_ctx,
            "tag_slug": tag_ctx,
            "tag_tree": tag_tree,
            "total_cards": total_cards,
            "user_email": _email,
        },
    )


@router.put("/cards/bulk/tags", response_class=HTMLResponse)
async def bulk_update_card_tags(
    request: Request,
    _email: Annotated[str, Depends(require_auth)],
    card_ids: Annotated[list[str], Form()] = [],
    tag_slugs: Annotated[list[str], Form()] = [],
    q: Annotated[str | None, Form()] = None,
    tag_slug: Annotated[str | None, Form()] = None,
) -> HTMLResponse:
    """Replace tags for all selected cards and return the refreshed card list + tags."""
    await card_service.bulk_update_card_tags(card_ids=card_ids, tag_slugs=tag_slugs)
    cards = await _cards_for_view(q, tag_slug)
    total_cards = len(await card_service.get_cards())
    all_tags = await tag_service.get_all_tags()
    counts = await card_service.get_card_counts_by_tag()
    tag_tree = tag_service.build_tag_tree(all_tags, counts)
    q_ctx = _normalize_filter_str(q)
    tag_ctx = _normalize_filter_str(tag_slug)
    return templates.TemplateResponse(
        request,
        "partials/card_list_with_tags.html",
        {
            "cards": cards,
            "q": q_ctx,
            "tag_slug": tag_ctx,
            "tag_tree": tag_tree,
            "total_cards": total_cards,
            "user_email": _email,
        },
    )


@router.delete("/cards/bulk", response_class=HTMLResponse)
async def bulk_delete_cards(
    request: Request,
    _email: Annotated[str, Depends(require_auth)],
    q: Annotated[str | None, Form()] = None,
    tag_slug: Annotated[str | None, Form()] = None,
) -> HTMLResponse:
    """Delete selected cards and their associated audio, then refresh cards + tags."""
    form = await request.form()
    form_card_ids = form.getlist("card_ids")
    query_card_ids = request.query_params.getlist("card_ids")
    card_ids = form_card_ids or query_card_ids
    audio_filenames = await card_service.bulk_delete_cards(card_ids=card_ids)
    for audio_filename in audio_filenames:
        await audio_service.delete_audio(audio_filename)
    cards = await _cards_for_view(q, tag_slug)
    total_cards = len(await card_service.get_cards())
    all_tags = await tag_service.get_all_tags()
    counts = await card_service.get_card_counts_by_tag()
    tag_tree = tag_service.build_tag_tree(all_tags, counts)
    q_ctx = _normalize_filter_str(q)
    tag_ctx = _normalize_filter_str(tag_slug)
    return templates.TemplateResponse(
        request,
        "partials/card_list_with_tags.html",
        {
            "cards": cards,
            "q": q_ctx,
            "tag_slug": tag_ctx,
            "tag_tree": tag_tree,
            "total_cards": total_cards,
            "user_email": _email,
        },
    )


@router.post("/cards/bulk/delete", response_class=HTMLResponse)
async def bulk_delete_cards_post(
    request: Request,
    _email: Annotated[str, Depends(require_auth)],
    q: Annotated[str | None, Form()] = None,
    tag_slug: Annotated[str | None, Form()] = None,
) -> HTMLResponse:
    """HTMX-friendly alias for bulk deletion using POST form submission."""
    return await bulk_delete_cards(
        request=request, _email=_email, q=q, tag_slug=tag_slug
    )


@router.delete("/cards/{card_id}", response_class=HTMLResponse)
async def delete_card(
    request: Request,
    _email: Annotated[str, Depends(require_auth)],
    card_id: str,
    q: Annotated[str | None, Query()] = None,
    tag_slug: Annotated[str | None, Query()] = None,
) -> HTMLResponse:
    """Delete a card and its associated audio, then return the updated card list."""
    audio_filename = await card_service.delete_card(card_id)
    if audio_filename:
        await audio_service.delete_audio(audio_filename)
    cards = await _cards_for_view(q, tag_slug)
    total_cards = len(await card_service.get_cards())
    all_tags = await tag_service.get_all_tags()
    counts = await card_service.get_card_counts_by_tag()
    tag_tree = tag_service.build_tag_tree(all_tags, counts)
    q_ctx = _normalize_filter_str(q)
    tag_ctx = _normalize_filter_str(tag_slug)
    return templates.TemplateResponse(
        request,
        "partials/card_list_with_tags.html",
        {
            "cards": cards,
            "q": q_ctx,
            "tag_slug": tag_ctx,
            "tag_tree": tag_tree,
            "total_cards": total_cards,
            "user_email": _email,
        },
    )
