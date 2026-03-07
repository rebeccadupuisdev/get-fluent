import re

from pydantic import ValidationError

from models.card import Card
from models.tag import Tag


async def _collect_ancestor_slugs(slug: str) -> list[str]:
    """Walk the parent_slug chain and return all slugs in that chain, including the starting slug."""
    slugs: list[str] = []
    current: str | None = slug
    seen: set[str] = set()

    while current and current not in seen:
        seen.add(current)
        slugs.append(current)
        tag = await Tag.find_one(Tag.slug == current)
        if tag is None:
            break
        current = tag.parent_slug

    return slugs


async def create_card(
    phrase: str,
    tag_slugs: list[str],
    audio_filename: str | None = None,
) -> Card:
    """Create a card, expanding each tag slug to include all ancestor slugs."""
    all_slugs: set[str] = set()
    for slug in tag_slugs:
        ancestors = await _collect_ancestor_slugs(slug)
        all_slugs.update(ancestors)

    card = Card(phrase=phrase, tag_slugs=list(all_slugs), audio_filename=audio_filename)
    await card.insert()
    return card


async def get_cards(tag_slug: str | None = None) -> list[Card]:
    """Return all cards sorted newest-first, optionally filtered by tag slug."""
    if tag_slug:
        query = Card.find({"tag_slugs": {"$in": [tag_slug]}})
    else:
        query = Card.find_all()
    return await query.sort("-created_at").to_list()


async def search_cards(query: str) -> list[Card]:
    """Return cards whose phrase matches query (case-insensitive), newest-first."""
    escaped = re.escape(query)
    return await Card.find({"phrase": {"$regex": escaped, "$options": "i"}}).sort("-created_at").to_list()


async def get_card_counts_by_tag() -> dict[str, int]:
    """Return a dict mapping each tag_slug to the number of cards assigned to it."""
    cards = await Card.find_all().to_list()
    counts: dict[str, int] = {}
    for card in cards:
        for slug in card.tag_slugs:
            counts[slug] = counts.get(slug, 0) + 1
    return counts


async def delete_card(card_id: str) -> str | None:
    """Delete a card by ID and return its audio_filename (or None if no audio).

    Returns None for both missing cards and malformed IDs.
    """
    try:
        card = await Card.get(card_id)
    except ValidationError:
        return None
    if card is None:
        return None
    audio_filename = card.audio_filename
    await card.delete()
    return audio_filename
