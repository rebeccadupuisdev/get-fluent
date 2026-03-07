from slugify import slugify

from models.tag import Tag


async def create_tag(name: str, parent_slug: str | None = None) -> Tag:
    """Slugify name, verify uniqueness, and insert a new Tag document."""
    slug = slugify(name)
    existing = await Tag.find_one(Tag.slug == slug)
    if existing:
        raise ValueError(f"A tag with slug '{slug}' already exists.")
    tag = Tag(name=name, slug=slug, parent_slug=parent_slug)
    await tag.insert()
    return tag


async def get_all_tags() -> list[Tag]:
    """Return all tags as a flat list."""
    return await Tag.find_all().to_list()


def build_tag_tree(tags: list[Tag]) -> list[dict]:
    """Return a nested list of {tag, children} dicts for sidebar display.

    Top-level tags (parent_slug is None) form the roots.
    Tags whose parent_slug does not match any known slug are also treated as roots.
    """
    by_slug: dict[str, dict] = {tag.slug: {"tag": tag, "children": []} for tag in tags}
    roots: list[dict] = []

    for tag in tags:
        node = by_slug[tag.slug]
        if tag.parent_slug and tag.parent_slug in by_slug:
            by_slug[tag.parent_slug]["children"].append(node)
        else:
            roots.append(node)

    return roots
