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


async def get_valid_parent_tags() -> list[Tag]:
    """Return tags that may be used as parents (root and level-1 tags only).

    Level-2 tags cannot be parents because that would create a disallowed
    third level. A tag is level-2 when its own parent is itself a child tag.
    """
    all_tags = await Tag.find_all().to_list()
    child_slugs = {tag.slug for tag in all_tags if tag.parent_slug is not None}
    return [
        tag
        for tag in all_tags
        if tag.parent_slug is None or tag.parent_slug not in child_slugs
    ]


def build_tag_tree(tags: list[Tag], counts: dict[str, int] | None = None) -> list[dict]:
    """Return a nested list of {tag, children, count} dicts for sidebar display.

    Top-level tags (parent_slug is None) form the roots.
    Tags whose parent_slug does not match any known slug are also treated as roots.
    counts maps tag slug to number of directly assigned cards.
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

    return roots
