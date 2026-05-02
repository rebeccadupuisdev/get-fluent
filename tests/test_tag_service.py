import pytest
from pydantic import ValidationError

from services.card_service import create_card
from services.tag_service import (
    build_tag_tree,
    create_tag,
    delete_empty_tags,
    get_all_tags,
    get_valid_parent_tags,
    reorder_tags,
    reparent_tag,
)


async def test_create_tag_no_parent():
    tag = await create_tag("Spanish")
    assert tag.name == "Spanish"
    assert tag.slug == "spanish"
    assert tag.parent_slug is None


async def test_create_tag_with_parent():
    parent = await create_tag("Spanish")
    child = await create_tag("Mexican Spanish", parent_slug=parent.slug)
    assert child.slug == "mexican-spanish"
    assert child.parent_slug == "spanish"


async def test_create_tag_slugifies_name():
    tag = await create_tag("Río de la Plata")
    assert tag.slug == "rio-de-la-plata"


async def test_create_tag_duplicate_raises():
    await create_tag("Spanish")
    with pytest.raises(ValueError, match="already exists"):
        await create_tag("Spanish")


async def test_create_tag_empty_name_raises():
    with pytest.raises(ValueError, match="empty"):
        await create_tag("")


async def test_create_tag_whitespace_only_name_raises():
    with pytest.raises(ValueError, match="empty"):
        await create_tag("   ")


async def test_create_tag_name_too_long_raises():
    """Tag name exceeding 100 chars raises ValidationError."""
    with pytest.raises(ValidationError):
        await create_tag("x" * 101)


async def test_create_tag_name_exactly_100_chars_succeeds():
    """Tag name at exactly 100 chars (boundary) is accepted."""
    tag = await create_tag("x" * 100)
    assert tag.name == "x" * 100
    assert len(tag.name) == 100


async def test_get_all_tags_empty():
    tags = await get_all_tags()
    assert tags == []


async def test_get_all_tags_returns_all():
    await create_tag("French")
    await create_tag("Spanish")
    tags = await get_all_tags()
    assert len(tags) == 2
    slugs = {t.slug for t in tags}
    assert slugs == {"french", "spanish"}


async def test_build_tag_tree_empty():
    assert build_tag_tree([]) == []


async def test_build_tag_tree_roots_only():
    await create_tag("French")
    await create_tag("Spanish")
    tags = await get_all_tags()
    tree = build_tag_tree(tags)
    assert len(tree) == 2
    assert all(node["children"] == [] for node in tree)


async def test_build_tag_tree_nested():
    parent = await create_tag("Spanish")
    child = await create_tag("Mexican Spanish", parent_slug=parent.slug)
    tags = await get_all_tags()
    tree = build_tag_tree(tags)

    assert len(tree) == 1
    root = tree[0]
    assert root["tag"].slug == "spanish"
    assert len(root["children"]) == 1
    assert root["children"][0]["tag"].slug == "mexican-spanish"
    assert root["children"][0]["children"] == []


async def test_build_tag_tree_three_levels():
    lang = await create_tag("Language")
    spanish = await create_tag("Spanish", parent_slug=lang.slug)
    await create_tag("Mexican Spanish", parent_slug=spanish.slug)
    tags = await get_all_tags()
    tree = build_tag_tree(tags)

    assert len(tree) == 1
    assert tree[0]["tag"].slug == "language"
    assert len(tree[0]["children"]) == 1
    assert len(tree[0]["children"][0]["children"]) == 1


async def test_build_tag_tree_orphan_treated_as_root():
    """A tag whose parent_slug doesn't match any known slug becomes a root node."""
    tag = await create_tag("Orphan")
    tag.parent_slug = "nonexistent-parent"
    tree = build_tag_tree([tag])
    assert len(tree) == 1
    assert tree[0]["tag"].slug == "orphan"


async def test_build_tag_tree_counts_included():
    await create_tag("French")
    await create_tag("Spanish")

    tags = await get_all_tags()
    counts = {"french": 3, "spanish": 7}
    tree = build_tag_tree(tags, counts)

    by_slug = {node["tag"].slug: node for node in tree}
    assert by_slug["french"]["count"] == 3
    assert by_slug["spanish"]["count"] == 7


async def test_build_tag_tree_missing_count_defaults_to_zero():
    await create_tag("French")

    tags = await get_all_tags()
    tree = build_tag_tree(tags, {})

    assert tree[0]["count"] == 0


async def test_build_tag_tree_counts_on_nested_tag():
    """Counts are applied to child nodes as well as root nodes."""
    parent = await create_tag("Spanish")
    child = await create_tag("Mexican Spanish", parent_slug=parent.slug)

    tags = await get_all_tags()
    counts = {parent.slug: 2, child.slug: 5}
    tree = build_tag_tree(tags, counts)

    root = tree[0]
    assert root["count"] == 2
    assert root["children"][0]["count"] == 5


async def test_create_tag_nonexistent_parent_raises():
    with pytest.raises(ValueError, match="does not exist"):
        await create_tag("Spanish", parent_slug="nonexistent")


async def test_create_tag_too_deep_raises():
    lang = await create_tag("Language")
    spanish = await create_tag("Spanish", parent_slug=lang.slug)
    mexican = await create_tag("Mexican Spanish", parent_slug=spanish.slug)

    with pytest.raises(ValueError, match="two levels"):
        await create_tag("CDMX Spanish", parent_slug=mexican.slug)


async def test_delete_empty_tags_no_tags():
    count = await delete_empty_tags()

    assert count == 0


async def test_delete_empty_tags_all_used():
    tag = await create_tag("French")
    await create_card(phrase="Bonjour", tag_slugs=[tag.slug])

    count = await delete_empty_tags()

    assert count == 0
    assert len(await get_all_tags()) == 1


async def test_delete_empty_tags_removes_unused():
    used_tag = await create_tag("Spanish")
    await create_tag("Unused")
    await create_card(phrase="Hola", tag_slugs=[used_tag.slug])

    count = await delete_empty_tags()

    assert count == 1
    remaining = await get_all_tags()
    assert len(remaining) == 1
    assert remaining[0].slug == "spanish"


async def test_delete_empty_tags_all_unused():
    await create_tag("French")
    await create_tag("Spanish")

    count = await delete_empty_tags()

    assert count == 2
    assert await get_all_tags() == []


async def test_get_valid_parent_tags_empty():
    tags = await get_valid_parent_tags()

    assert tags == []


async def test_get_valid_parent_tags_roots_only():
    await create_tag("French")
    await create_tag("Spanish")

    valid = await get_valid_parent_tags()

    assert len(valid) == 2


async def test_get_valid_parent_tags_excludes_level2():
    root = await create_tag("Language")
    l1 = await create_tag("Spanish", parent_slug=root.slug)
    await create_tag("Mexican Spanish", parent_slug=l1.slug)

    valid = await get_valid_parent_tags()
    slugs = {t.slug for t in valid}

    assert "mexican-spanish" not in slugs
    assert "spanish" in slugs
    assert "language" in slugs


async def test_get_valid_parent_tags_single_root():
    await create_tag("French")

    valid = await get_valid_parent_tags()

    assert len(valid) == 1
    assert valid[0].slug == "french"


# ---------------------------------------------------------------------------
# reorder_tags
# ---------------------------------------------------------------------------


async def test_reorder_root_tags_updates_order():
    await create_tag("French")
    await create_tag("Spanish")
    await create_tag("German")

    await reorder_tags(["german", "french", "spanish"], parent_slug=None)

    tags = await get_all_tags()
    by_slug = {t.slug: t for t in tags}
    assert by_slug["german"].order == 0
    assert by_slug["french"].order == 1
    assert by_slug["spanish"].order == 2


async def test_reorder_child_tags_updates_order():
    parent = await create_tag("Spanish")
    await create_tag("Mexican Spanish", parent_slug=parent.slug)
    await create_tag("Argentinian Spanish", parent_slug=parent.slug)

    await reorder_tags(
        ["argentinian-spanish", "mexican-spanish"],
        parent_slug="spanish",
    )

    tags = await get_all_tags()
    by_slug = {t.slug: t for t in tags}
    assert by_slug["argentinian-spanish"].order == 0
    assert by_slug["mexican-spanish"].order == 1


async def test_reorder_tags_raises_for_wrong_group():
    await create_tag("French")
    await create_tag("Spanish")
    parent = await create_tag("Language")
    await create_tag("German", parent_slug=parent.slug)

    with pytest.raises(ValueError, match="does not belong"):
        await reorder_tags(["french", "german"], parent_slug=None)


async def test_build_tag_tree_respects_order():
    t1 = await create_tag("Aardvark")
    t2 = await create_tag("Zebra")
    t3 = await create_tag("Mango")
    t1.order = 2
    await t1.save()
    t2.order = 0
    await t2.save()
    t3.order = 1
    await t3.save()

    tags = await get_all_tags()
    tree = build_tag_tree(tags)

    assert [n["tag"].slug for n in tree] == ["zebra", "mango", "aardvark"]


# ---------------------------------------------------------------------------
# reparent_tag
# ---------------------------------------------------------------------------


async def test_reparent_tag_to_root():
    parent = await create_tag("Spanish")
    child = await create_tag("Mexican Spanish", parent_slug=parent.slug)
    assert child.parent_slug == "spanish"

    await reparent_tag(child.slug, None)

    from models.tag import Tag

    updated = await Tag.find_one(Tag.slug == child.slug)
    assert updated.parent_slug is None


async def test_reparent_tag_adopt_into_parent():
    root_a = await create_tag("Spanish")
    root_b = await create_tag("French")

    await reparent_tag(root_b.slug, root_a.slug)

    from models.tag import Tag

    updated = await Tag.find_one(Tag.slug == root_b.slug)
    assert updated.parent_slug == "spanish"


async def test_reparent_tag_noop_same_parent():
    parent = await create_tag("Spanish")
    child = await create_tag("Mexican Spanish", parent_slug=parent.slug)

    await reparent_tag(child.slug, parent.slug)

    from models.tag import Tag

    updated = await Tag.find_one(Tag.slug == child.slug)
    assert updated.parent_slug == "spanish"


async def test_reparent_tag_nonexistent_raises():
    with pytest.raises(ValueError, match="does not exist"):
        await reparent_tag("nonexistent", None)


async def test_reparent_tag_nonexistent_parent_raises():
    tag = await create_tag("Spanish")
    with pytest.raises(ValueError, match="does not exist"):
        await reparent_tag(tag.slug, "nonexistent-parent")


async def test_reparent_tag_self_raises():
    tag = await create_tag("Spanish")
    with pytest.raises(ValueError, match="own parent"):
        await reparent_tag(tag.slug, tag.slug)


async def test_reparent_tag_into_own_child_raises():
    parent = await create_tag("Spanish")
    child = await create_tag("Mexican Spanish", parent_slug=parent.slug)
    with pytest.raises(ValueError, match="own children"):
        await reparent_tag(parent.slug, child.slug)


async def test_reparent_tag_with_children_into_non_root_raises():
    root = await create_tag("Root")
    mid = await create_tag("Mid", parent_slug=root.slug)
    branch = await create_tag("Branch")
    await create_tag("Leaf", parent_slug=branch.slug)

    with pytest.raises(ValueError, match="non-root"):
        await reparent_tag(branch.slug, mid.slug)


async def test_reparent_tag_with_children_into_root_succeeds():
    root_a = await create_tag("Root A")
    root_b = await create_tag("Root B")
    await create_tag("Child", parent_slug=root_b.slug)

    await reparent_tag(root_b.slug, root_a.slug)

    from models.tag import Tag

    updated = await Tag.find_one(Tag.slug == root_b.slug)
    assert updated.parent_slug == "root-a"


async def test_reparent_tag_too_deep_raises():
    """Cannot adopt a tag whose new parent is already at depth 2."""
    root = await create_tag("Root")
    mid = await create_tag("Mid", parent_slug=root.slug)
    leaf = await create_tag("Leaf", parent_slug=mid.slug)
    orphan = await create_tag("Orphan")

    with pytest.raises(ValueError, match="two levels"):
        await reparent_tag(orphan.slug, leaf.slug)


async def test_build_tag_tree_children_respect_order():
    parent = await create_tag("Parent")
    c1 = await create_tag("Alpha", parent_slug=parent.slug)
    c2 = await create_tag("Beta", parent_slug=parent.slug)
    c1.order = 1
    await c1.save()
    c2.order = 0
    await c2.save()

    tags = await get_all_tags()
    tree = build_tag_tree(tags)

    children = tree[0]["children"]
    assert [n["tag"].slug for n in children] == ["beta", "alpha"]
