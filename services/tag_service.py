from slugify import slugify

from models.tag import Tag


async def create_tag(name: str, parent_slug: str | None = None) -> Tag:
    """Slugify name, verify uniqueness, and insert a new Tag document.

    Tags support at most two levels of nesting (root → level 1 → level 2).
    Raises ValueError if the chosen parent is already a level-1 tag (i.e. it
    has its own parent), which would produce a disallowed third level.
    Raises ValueError if name is empty or whitespace-only.
    """
    if not name or not name.strip():
        raise ValueError("Tag name must not be empty.")
    slug = slugify(name)
    existing = await Tag.find_one(Tag.slug == slug)
    if existing:
        raise ValueError(f"A tag '{slug}' already exists.")

    if parent_slug:
        parent = await Tag.find_one(Tag.slug == parent_slug)
        if parent is None:
            raise ValueError(f"Parent tag '{parent_slug}' does not exist.")
        if parent.parent_slug is not None:
            grandparent = await Tag.find_one(Tag.slug == parent.parent_slug)
            if grandparent is not None and grandparent.parent_slug is not None:
                raise ValueError(
                    "Tags only support two levels of nesting. "
                    f"'{parent.name}' is already a level-2 tag and cannot have children of its own."
                )

    tag = Tag(name=name, slug=slug, parent_slug=parent_slug)
    await tag.insert()
    return tag


async def get_all_tags() -> list[Tag]:
    """Return all tags as a flat list."""
    return await Tag.find_all().to_list()


async def delete_empty_tags() -> int:
    """Delete all tags that are not attached to any card.

    Returns the number of tags deleted.
    """
    from models.card import Card

    all_tags = await Tag.find_all().to_list()
    used_slugs: set[str] = set()
    async for card in Card.find_all():
        used_slugs.update(card.tag_slugs)

    deleted = 0
    for tag in all_tags:
        if tag.slug not in used_slugs:
            await tag.delete()
            deleted += 1
    return deleted


def flatten_tag_tree_preorder(tree: list[dict]) -> list[Tag]:
    """Depth-first preorder of tag nodes (matches sidebar / modal checkbox order)."""
    out: list[Tag] = []
    for node in tree:
        out.append(node["tag"])
        out.extend(flatten_tag_tree_preorder(node["children"]))
    return out


async def get_valid_parent_tags() -> list[Tag]:
    """Return tags that may be used as parents (root and level-1 tags only).

    Level-2 tags cannot be parents because that would create a disallowed
    third level. A tag is level-2 when its own parent is itself a child tag.
    Order matches the tag tree (``order`` field within each group).
    """
    all_tags = await Tag.find_all().to_list()
    child_slugs = {tag.slug for tag in all_tags if tag.parent_slug is not None}
    valid_slugs = {
        tag.slug
        for tag in all_tags
        if tag.parent_slug is None or tag.parent_slug not in child_slugs
    }
    tree = build_tag_tree(all_tags)
    return [t for t in flatten_tag_tree_preorder(tree) if t.slug in valid_slugs]


def build_tag_tree(tags: list[Tag], counts: dict[str, int] | None = None) -> list[dict]:
    """Return a nested list of {tag, children, count} dicts for sidebar display.

    Top-level tags (parent_slug is None) form the roots.
    Tags whose parent_slug does not match any known slug are also treated as roots.
    counts maps tag slug to number of directly assigned cards.
    Roots and children are sorted by their order field.
    """
    counts = counts or {}
    by_slug: dict[str, dict] = {
        tag.slug: {"tag": tag, "children": [], "count": counts.get(tag.slug, 0)}
        for tag in tags
    }
    roots: list[dict] = []

    for tag in tags:
        node = by_slug[tag.slug]
        if tag.parent_slug and tag.parent_slug in by_slug:
            by_slug[tag.parent_slug]["children"].append(node)
        else:
            roots.append(node)

    roots.sort(key=lambda n: n["tag"].order)
    for node in by_slug.values():
        node["children"].sort(key=lambda n: n["tag"].order)

    return roots


async def _next_order_among_siblings(
    parent_slug: str | None,
    exclude_slug: str,
) -> int:
    """Largest order among tags in the group plus one (append at end)."""
    if parent_slug is None:
        siblings = await Tag.find(Tag.parent_slug == None).to_list()
    else:
        siblings = await Tag.find(Tag.parent_slug == parent_slug).to_list()
    others = [t for t in siblings if t.slug != exclude_slug]
    return max((t.order for t in others), default=-1) + 1


async def reparent_tag(slug: str, new_parent_slug: str | None) -> None:
    """Move a tag to a new parent, or promote it to root if new_parent_slug is None.

    Raises ValueError if:
    - The tag does not exist
    - The new parent does not exist
    - The move would create a circular reference
    - The move would exceed the maximum nesting depth of 2
    - The tag has children and the new parent is not a root tag
    """
    tag = await Tag.find_one(Tag.slug == slug)
    if tag is None:
        raise ValueError(f"Tag '{slug}' does not exist.")

    if tag.parent_slug == new_parent_slug:
        return

    if new_parent_slug is None:
        tag.parent_slug = None
        tag.order = await _next_order_among_siblings(None, slug)
        await tag.save()
        return

    if new_parent_slug == slug:
        raise ValueError("A tag cannot be its own parent.")

    new_parent = await Tag.find_one(Tag.slug == new_parent_slug)
    if new_parent is None:
        raise ValueError(f"Parent tag '{new_parent_slug}' does not exist.")

    if new_parent.parent_slug == slug:
        raise ValueError("Cannot move a tag into one of its own children.")

    if new_parent.parent_slug is not None:
        grandparent = await Tag.find_one(Tag.slug == new_parent.parent_slug)
        if grandparent is not None and grandparent.parent_slug is not None:
            raise ValueError("Tags only support two levels of nesting.")

    children = await Tag.find(Tag.parent_slug == slug).to_list()
    if children and new_parent.parent_slug is not None:
        raise ValueError(
            "Cannot move a tag with children under a non-root tag."
        )

    tag.parent_slug = new_parent_slug
    tag.order = await _next_order_among_siblings(new_parent_slug, slug)
    await tag.save()


async def reorder_tags(slugs: list[str], parent_slug: str | None) -> None:
    """Update the display order of tags within a group.

    slugs is the desired order of tag slugs within the group (root tags when
    parent_slug is None, or children of the given parent otherwise).
    Raises ValueError if any slug does not belong to the specified group.
    """
    for i, slug in enumerate(slugs):
        tag = await Tag.find_one(Tag.slug == slug)
        if tag is None:
            continue
        if tag.parent_slug != parent_slug:
            raise ValueError(
                f"Tag '{slug}' does not belong to the specified group."
            )
        tag.order = i
        await tag.save()
