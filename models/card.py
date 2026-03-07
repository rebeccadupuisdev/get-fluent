from datetime import datetime, timezone

from beanie import Document
from pydantic import Field


class Card(Document):
    phrase: str
    audio_filename: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tag_slugs: list[str] = []

    class Settings:
        name = "cards"
