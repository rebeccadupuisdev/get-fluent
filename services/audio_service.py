import os
import uuid
from pathlib import Path

import aiofiles
from fastapi import UploadFile

AUDIO_DIR = Path(os.getenv("AUDIO_DIR", "frontend/static/content"))
ALLOWED_AUDIO_EXTENSIONS = frozenset({".mp3", ".wav", ".ogg", ".m4a", ".webm"})


async def save_audio(file: UploadFile) -> str:
    """Write the uploaded file to AUDIO_DIR with a UUID filename; return the filename.
    Only allows known audio extensions; others use .bin to prevent XSS via uploaded .html etc.
    """
    raw_suffix = Path(file.filename).suffix.lower() if file.filename else ""
    suffix = raw_suffix if raw_suffix in ALLOWED_AUDIO_EXTENSIONS else ".bin"
    filename = f"{uuid.uuid4().hex}{suffix}"
    dest = AUDIO_DIR / filename
    async with aiofiles.open(dest, "wb") as out:
        content = await file.read()
        await out.write(content)
    return filename


async def save_audio_bytes(data: bytes, suffix: str = ".wav") -> str:
    """Write raw audio bytes to AUDIO_DIR with a UUID filename; return the filename."""
    safe_suffix = suffix if suffix in ALLOWED_AUDIO_EXTENSIONS else ".bin"
    filename = f"{uuid.uuid4().hex}{safe_suffix}"
    dest = AUDIO_DIR / filename
    async with aiofiles.open(dest, "wb") as out:
        await out.write(data)
    return filename


async def delete_audio(filename: str) -> None:
    """Delete an audio file from AUDIO_DIR if it exists.
    Rejects path traversal (e.g. ../../../etc/passwd).
    """
    path = (AUDIO_DIR / filename).resolve()
    if not path.is_relative_to(AUDIO_DIR.resolve()):
        raise ValueError("Invalid filename: path traversal not allowed")
    if path.exists():
        path.unlink()
