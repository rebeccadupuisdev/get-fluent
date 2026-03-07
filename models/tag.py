from beanie import Document


class Tag(Document):
    name: str
    slug: str
    parent_slug: str | None = None

    class Settings:
        name = "tags"
