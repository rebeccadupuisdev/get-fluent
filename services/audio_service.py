import uuid
from pathlib import Path

import aiofiles
from fastapi import UploadFile

AUDIO_DIR = Path("frontend/static/content")


async def save_audio(file: UploadFile) -> str:
    """Write the uploaded file to AUDIO_DIR with a UUID filename; return the filename."""
    suffix = Path(file.filename).suffix if file.filename else ".bin"
    filename = f"{uuid.uuid4().hex}{suffix}"
    dest = AUDIO_DIR / filename
    async with aiofiles.open(dest, "wb") as out:
        content = await file.read()
        await out.write(content)
    return filename


async def delete_audio(filename: str) -> None:
    """Delete an audio file from AUDIO_DIR if it exists."""
    path = AUDIO_DIR / filename
    if path.exists():
        path.unlink()
