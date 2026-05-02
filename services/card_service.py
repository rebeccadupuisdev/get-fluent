import re
import unicodedata
from collections import defaultdict

from pydantic import ValidationError

from models.card import Card
from models.tag import Tag

# Maps NFD base letter (lowercase) -> regex character class matching any letter with that base (accents ignored).
_LETTER_VARIANT_CLASS: dict[str, str] | None = None


def _ensure_letter_variant_classes() -> dict[str, str]:
    """Build once: all Unicode letters grouped by first NFD codepoint (lower), as regex char classes."""
    global _LETTER_VARIANT_CLASS
    if _LETTER_VARIANT_CLASS is not None:
        return _LETTER_VARIANT_CLASS

    base_to_chars: defaultdict[str, set[str]] = defaultdict(set)

    for code in range(0x110000):
        try:
            ch = chr(code)
        except ValueError:
            break
        if unicodedata.category(ch)[0] != "L":
            continue
        nfd = unicodedata.normalize("NFD", ch)
        if not nfd:
            continue
        base_key = nfd[0].lower()
        base_to_chars[base_key].add(ch)

    classes: dict[str, str] = {}
    for base_key, chars in base_to_chars.items():
        escaped: list[str] = []
        for c in sorted(chars):
            if c in r"\]-^":
                escaped.append("\\" + c)
            elif c == "-":
                escaped.append(r"\-")
            else:
                escaped.append(c)
        classes[base_key] = "[" + "".join(escaped) + "]"

    _LETTER_VARIANT_CLASS = classes
    return classes


def _accent_insensitive_regex_pattern(query: str) -> str:
    """Literal substring match against NFC text; letters match any accented variant (case handled by regex i flag)."""
    query = unicodedata.normalize("NFC", query)
    classes = _ensure_letter_variant_classes()
    parts: list[str] = []
    for ch in query:
        if ch.isalpha():
            nfd = unicodedata.normalize("NFD", ch)
            base_key = nfd[0].lower()
            fragment = classes.get(base_key)
            if fragment is None:
                fragment = re.escape(ch)
            parts.append(fragment)
        else:
            parts.append(re.escape(ch))
    return "".join(parts)


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
    translation: str | None = None,
) -> Card:
    """Create a card, expanding each tag slug to include all ancestor slugs."""
    if not phrase or not phrase.strip():
        raise ValueError("Phrase must not be empty.")
    all_slugs: set[str] = set()
    for slug in tag_slugs:
        ancestors = await _collect_ancestor_slugs(slug)
        all_slugs.update(ancestors)

    card = Card(
        phrase=phrase,
        translation=translation,
        tag_slugs=list(all_slugs),
        audio_filename=audio_filename,
    )
    await card.insert()
    return card


async def get_cards(tag_slug: str | None = None) -> list[Card]:
    """Return all cards sorted newest-first, optionally filtered by tag slug."""
    if tag_slug:
        query = Card.find({"tag_slugs": {"$in": [tag_slug]}})
    else:
        query = Card.find_all()
    return await query.sort("-created_at").to_list()


async def search_cards(query: str, tag_slug: str | None = None) -> list[Card]:
    """Return cards whose phrase or translation matches query (case- and accent-insensitive), newest-first.

    If tag_slug is provided, results are further restricted to cards assigned to that tag.
    """
    pattern = _accent_insensitive_regex_pattern(query)
    regex = {"$regex": pattern, "$options": "i"}
    filters: dict = {"$or": [{"phrase": regex}, {"translation": regex}]}
    if tag_slug:
        filters["tag_slugs"] = {"$in": [tag_slug]}
    return await Card.find(filters).sort("-created_at").to_list()


async def get_card_counts_by_tag() -> dict[str, int]:
    """Return a dict mapping each tag_slug to the number of cards assigned to it."""
    cards = await Card.find_all().to_list()
    counts: dict[str, int] = {}
    for card in cards:
        for slug in card.tag_slugs:
            counts[slug] = counts.get(slug, 0) + 1
    return counts


async def get_card(card_id: str) -> Card | None:
    """Get a single card by ID, returning None for missing or invalid IDs."""
    try:
        return await Card.get(card_id)
    except Exception:
        return None


async def update_card(
    card_id: str,
    phrase: str,
    tag_slugs: list[str],
    audio_filename: str | None,
    translation: str | None = None,
) -> Card | None:
    """Update a card's phrase, translation, tags, and audio. Returns the updated card or None."""
    try:
        card = await Card.get(card_id)
    except ValidationError:
        return None
    if card is None:
        return None

    if not phrase or not phrase.strip():
        raise ValueError("Phrase must not be empty.")

    all_slugs: set[str] = set()
    for slug in tag_slugs:
        ancestors = await _collect_ancestor_slugs(slug)
        all_slugs.update(ancestors)

    card.phrase = phrase
    card.translation = translation
    card.tag_slugs = list(all_slugs)
    card.audio_filename = audio_filename
    await card.save()
    return card


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


async def bulk_update_card_tags(card_ids: list[str], tag_slugs: list[str]) -> int:
    """Replace tags for multiple cards, expanding each selected tag to its ancestors.

    Returns the number of cards updated. Invalid or missing IDs are ignored.
    """
    all_slugs: set[str] = set()
    for slug in tag_slugs:
        ancestors = await _collect_ancestor_slugs(slug)
        all_slugs.update(ancestors)

    updated = 0
    for card_id in card_ids:
        try:
            card = await Card.get(card_id)
        except Exception:
            card = None
        if card is None:
            continue
        card.tag_slugs = list(all_slugs)
        await card.save()
        updated += 1

    return updated


async def bulk_delete_cards(card_ids: list[str]) -> list[str]:
    """Delete multiple cards and return associated audio filenames.

    Invalid or missing card IDs are ignored.
    """
    deleted_audio_filenames: list[str] = []
    for card_id in card_ids:
        try:
            card = await Card.get(card_id)
        except Exception:
            card = None
        if card is None:
            continue
        if card.audio_filename:
            deleted_audio_filenames.append(card.audio_filename)
        await card.delete()
    return deleted_audio_filenames
