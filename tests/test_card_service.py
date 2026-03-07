from datetime import datetime, timedelta, timezone

from bson import ObjectId

from models.card import Card
from services.card_service import create_card, delete_card, get_cards, search_cards
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
