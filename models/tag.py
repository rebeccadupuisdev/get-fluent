from beanie import Document
from pydantic import Field


class Tag(Document):
    name: str = Field(max_length=100)
    slug: str
    parent_slug: str | None = None

    class Settings:
        name = "tags"
