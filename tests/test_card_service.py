from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId

from models.card import Card
from services.card_service import (
    create_card,
    delete_card,
    get_card,
    get_card_counts_by_tag,
    get_cards,
    search_cards,
    update_card,
)
from services.tag_service import create_tag


async def test_create_card_no_tags():
    card = await create_card(phrase="Hello world", tag_slugs=[])
    assert card.phrase == "Hello world"
    assert card.tag_slugs == []
    assert card.audio_filename is None
    assert card.id is not None


async def test_create_card_with_audio():
    card = await create_card(phrase="Bonjour", tag_slugs=[], audio_filename="test.mp3")
    assert card.audio_filename == "test.mp3"


async def test_create_card_stores_ancestor_slugs():
    grandparent = await create_tag("Language")
    parent = await create_tag("Spanish", parent_slug=grandparent.slug)
    child = await create_tag("Mexican Spanish", parent_slug=parent.slug)

    card = await create_card(phrase="¿Qué tal?", tag_slugs=[child.slug])
    assert set(card.tag_slugs) == {"mexican-spanish", "spanish", "language"}


async def test_create_card_deduplicates_ancestor_slugs():
    parent = await create_tag("Spanish")
    child = await create_tag("Mexican Spanish", parent_slug=parent.slug)

    card = await create_card(phrase="Hola", tag_slugs=[child.slug, parent.slug])
    assert card.tag_slugs.count("spanish") == 1


async def test_create_card_unknown_tag_slug_still_stored():
    """An unrecognised slug is stored as-is — the walk just ends immediately."""
    card = await create_card(phrase="Test", tag_slugs=["unknown-slug"])
    assert "unknown-slug" in card.tag_slugs


async def test_create_card_empty_phrase_raises():
    """Empty or whitespace-only phrase raises ValueError."""
    with pytest.raises(ValueError, match="must not be empty"):
        await create_card(phrase="", tag_slugs=[])


async def test_create_card_whitespace_only_phrase_raises():
    """Whitespace-only phrase raises ValueError."""
    with pytest.raises(ValueError, match="must not be empty"):
        await create_card(phrase="   ", tag_slugs=[])


async def test_get_cards_empty():
    cards = await get_cards()
    assert cards == []


async def test_get_cards_newest_first():
    now = datetime.now(timezone.utc)
    old = Card(phrase="Old", created_at=now - timedelta(seconds=2), tag_slugs=[])
    new = Card(phrase="New", created_at=now, tag_slugs=[])
    await old.insert()
    await new.insert()

    cards = await get_cards()
    assert cards[0].phrase == "New"
    assert cards[1].phrase == "Old"


async def test_get_cards_tag_filter():
    tag = await create_tag("French")
    await create_card(phrase="Bonjour", tag_slugs=[tag.slug])
    await create_card(phrase="Hello", tag_slugs=[])

    filtered = await get_cards(tag_slug="french")
    assert len(filtered) == 1
    assert filtered[0].phrase == "Bonjour"


async def test_get_cards_tag_filter_no_match():
    await create_tag("French")
    await create_card(phrase="Hello", tag_slugs=[])

    filtered = await get_cards(tag_slug="french")
    assert filtered == []


async def test_get_cards_tag_filter_matches_ancestor():
    """Filtering by an ancestor slug returns cards tagged with a descendant."""
    parent = await create_tag("Spanish")
    child = await create_tag("Mexican Spanish", parent_slug=parent.slug)
    await create_card(phrase="¿Cómo estás?", tag_slugs=[child.slug])

    by_parent = await get_cards(tag_slug="spanish")
    assert len(by_parent) == 1
    assert by_parent[0].phrase == "¿Cómo estás?"


async def test_search_cards_case_insensitive():
    await create_card(phrase="Buenos días", tag_slugs=[])
    await create_card(phrase="Buenas noches", tag_slugs=[])
    await create_card(phrase="Bonjour", tag_slugs=[])

    results = await search_cards("BUEN")
    assert len(results) == 2
    assert all("buen" in r.phrase.lower() for r in results)


async def test_search_cards_no_match():
    await create_card(phrase="Hello", tag_slugs=[])
    results = await search_cards("xyz123")
    assert results == []


async def test_search_cards_empty_query_returns_all():
    """An empty query string matches all cards."""
    await create_card(phrase="Hola", tag_slugs=[])
    await create_card(phrase="Bonjour", tag_slugs=[])

    results = await search_cards("")

    assert len(results) == 2


async def test_search_cards_regex_special_characters():
    """Regex metacharacters in the query are treated as literals."""
    await create_card(phrase="(test)", tag_slugs=[])
    await create_card(phrase="no match", tag_slugs=[])

    results = await search_cards("(test)")

    assert len(results) == 1
    assert results[0].phrase == "(test)"


async def test_search_cards_dot_does_not_match_any_char():
    """A literal dot in the query does not act as a regex wildcard."""
    await create_card(phrase="a.b", tag_slugs=[])
    await create_card(phrase="axb", tag_slugs=[])

    results = await search_cards("a.b")

    assert len(results) == 1
    assert results[0].phrase == "a.b"


async def test_search_cards_newest_first():
    now = datetime.now(timezone.utc)
    old = Card(phrase="Hola amigo", created_at=now - timedelta(seconds=2), tag_slugs=[])
    new = Card(phrase="Hola mundo", created_at=now, tag_slugs=[])
    await old.insert()
    await new.insert()

    results = await search_cards("hola")
    assert results[0].phrase == "Hola mundo"
    assert results[1].phrase == "Hola amigo"


async def test_delete_card_returns_audio_filename():
    card = await create_card(phrase="Test", tag_slugs=[], audio_filename="audio.mp3")
    returned = await delete_card(str(card.id))
    assert returned == "audio.mp3"
    assert await Card.get(card.id) is None


async def test_delete_card_no_audio_returns_none():
    card = await create_card(phrase="No audio", tag_slugs=[])
    returned = await delete_card(str(card.id))
    assert returned is None
    assert await Card.get(card.id) is None


async def test_delete_card_not_found_returns_none():
    fake_id = str(ObjectId())
    result = await delete_card(fake_id)
    assert result is None


async def test_delete_card_malformed_id_returns_none():
    """A non-ObjectId string does not raise; service returns None gracefully."""
    result = await delete_card("not-a-valid-object-id")
    assert result is None


async def test_get_card_counts_by_tag_no_cards():
    counts = await get_card_counts_by_tag()

    assert counts == {}


async def test_get_card_counts_by_tag_no_tags_returns_empty():
    await create_card(phrase="Hello", tag_slugs=[])

    counts = await get_card_counts_by_tag()

    assert counts == {}


async def test_get_card_counts_by_tag_single_card():
    tag = await create_tag("French")
    await create_card(phrase="Bonjour", tag_slugs=[tag.slug])

    counts = await get_card_counts_by_tag()

    assert counts["french"] == 1


async def test_get_card_counts_by_tag_multiple_cards_same_tag():
    tag = await create_tag("Spanish")
    await create_card(phrase="Hola", tag_slugs=[tag.slug])
    await create_card(phrase="Adios", tag_slugs=[tag.slug])

    counts = await get_card_counts_by_tag()

    assert counts["spanish"] == 2


async def test_get_card_counts_by_tag_counts_each_slug_independently():
    """Ancestor slugs expanded onto a card each contribute to their own count."""
    parent = await create_tag("Spanish")
    child = await create_tag("Mexican Spanish", parent_slug=parent.slug)
    await create_card(phrase="¿Qué tal?", tag_slugs=[child.slug])

    counts = await get_card_counts_by_tag()

    assert counts["mexican-spanish"] == 1
    assert counts["spanish"] == 1


async def test_get_card_counts_by_tag_multiple_tags_on_one_card():
    tag_a = await create_tag("French")
    tag_b = await create_tag("Greetings")
    await create_card(phrase="Bonjour", tag_slugs=[tag_a.slug, tag_b.slug])

    counts = await get_card_counts_by_tag()

    assert counts["french"] == 1
    assert counts["greetings"] == 1


# ---------------------------------------------------------------------------
# search_cards — tag_slug filter
# ---------------------------------------------------------------------------


async def test_search_cards_with_tag_slug_returns_only_matching_tag():
    tag = await create_tag("French")
    await create_card(phrase="Bonjour", tag_slugs=[tag.slug])
    await create_card(phrase="Bonsoir", tag_slugs=[])

    results = await search_cards("bon", tag_slug="french")

    assert len(results) == 1
    assert results[0].phrase == "Bonjour"


async def test_search_cards_with_tag_slug_no_match_returns_empty():
    tag = await create_tag("Spanish")
    await create_card(phrase="Hola", tag_slugs=[tag.slug])

    results = await search_cards("hola", tag_slug="french")

    assert results == []


async def test_search_cards_with_tag_slug_newest_first():
    now = datetime.now(timezone.utc)
    tag = await create_tag("French")
    old = Card(phrase="Bonjour", created_at=now - timedelta(seconds=2), tag_slugs=["french"])
    new = Card(phrase="Bonsoir", created_at=now, tag_slugs=["french"])
    await old.insert()
    await new.insert()

    results = await search_cards("bon", tag_slug="french")

    assert results[0].phrase == "Bonsoir"
    assert results[1].phrase == "Bonjour"


# ---------------------------------------------------------------------------
# get_card
# ---------------------------------------------------------------------------


async def test_get_card_returns_card():
    card = await create_card(phrase="Merci", tag_slugs=[])

    result = await get_card(str(card.id))

    assert result is not None
    assert result.phrase == "Merci"


async def test_get_card_not_found_returns_none():
    from bson import ObjectId

    result = await get_card(str(ObjectId()))

    assert result is None


async def test_get_card_malformed_id_returns_none():
    result = await get_card("not-a-valid-id")

    assert result is None


# ---------------------------------------------------------------------------
# update_card
# ---------------------------------------------------------------------------


async def test_update_card_changes_phrase():
    card = await create_card(phrase="Salut", tag_slugs=[])

    updated = await update_card(str(card.id), phrase="Allo", tag_slugs=[], audio_filename=None)

    assert updated is not None
    assert updated.phrase == "Allo"


async def test_update_card_persists_to_db():
    card = await create_card(phrase="Salut", tag_slugs=[])

    await update_card(str(card.id), phrase="Allo", tag_slugs=[], audio_filename=None)

    refreshed = await Card.get(card.id)
    assert refreshed is not None
    assert refreshed.phrase == "Allo"


async def test_update_card_expands_ancestor_slugs():
    grandparent = await create_tag("Language")
    parent = await create_tag("Spanish", parent_slug=grandparent.slug)
    child = await create_tag("Mexican Spanish", parent_slug=parent.slug)
    card = await create_card(phrase="Hola", tag_slugs=[])

    updated = await update_card(str(card.id), phrase="Hola", tag_slugs=[child.slug], audio_filename=None)

    assert updated is not None
    assert set(updated.tag_slugs) == {"mexican-spanish", "spanish", "language"}


async def test_update_card_clears_tags_when_empty():
    tag = await create_tag("French")
    card = await create_card(phrase="Bonjour", tag_slugs=[tag.slug])

    updated = await update_card(str(card.id), phrase="Bonjour", tag_slugs=[], audio_filename=None)

    assert updated is not None
    assert updated.tag_slugs == []


async def test_update_card_sets_audio_filename():
    card = await create_card(phrase="Test", tag_slugs=[])

    updated = await update_card(str(card.id), phrase="Test", tag_slugs=[], audio_filename="new.mp3")

    assert updated is not None
    assert updated.audio_filename == "new.mp3"


async def test_update_card_clears_audio_filename():
    card = await create_card(phrase="Test", tag_slugs=[], audio_filename="old.mp3")

    updated = await update_card(str(card.id), phrase="Test", tag_slugs=[], audio_filename=None)

    assert updated is not None
    assert updated.audio_filename is None


async def test_update_card_not_found_returns_none():
    from bson import ObjectId

    result = await update_card(str(ObjectId()), phrase="X", tag_slugs=[], audio_filename=None)

    assert result is None


async def test_update_card_malformed_id_returns_none():
    result = await update_card("not-a-valid-id", phrase="X", tag_slugs=[], audio_filename=None)

    assert result is None


async def test_update_card_empty_phrase_raises():
    """Update with empty or whitespace-only phrase raises ValueError."""
    card = await create_card(phrase="Salut", tag_slugs=[])

    with pytest.raises(ValueError, match="must not be empty"):
        await update_card(str(card.id), phrase="", tag_slugs=[], audio_filename=None)


async def test_update_card_whitespace_only_phrase_raises():
    """Update with whitespace-only phrase raises ValueError."""
    card = await create_card(phrase="Salut", tag_slugs=[])

    with pytest.raises(ValueError, match="must not be empty"):
        await update_card(str(card.id), phrase="   ", tag_slugs=[], audio_filename=None)
