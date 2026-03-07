import pytest

from services.tag_service import build_tag_tree, create_tag, get_all_tags


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
