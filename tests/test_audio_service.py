from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

import services.audio_service as audio_service


@pytest.fixture
def audio_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect AUDIO_DIR to a temporary directory for each test."""
    monkeypatch.setattr(audio_service, "AUDIO_DIR", tmp_path)
    return tmp_path


def make_upload_file(content: bytes = b"audio data", filename: str = "test.mp3") -> MagicMock:
    """Return a minimal UploadFile-like mock."""
    mock = MagicMock()
    mock.filename = filename
    mock.read = AsyncMock(return_value=content)
    return mock


async def test_save_audio_returns_filename_with_correct_suffix(audio_dir: Path):
    upload = make_upload_file(filename="clip.mp3")

    filename = await audio_service.save_audio(upload)

    assert filename.endswith(".mp3")


async def test_save_audio_writes_content_to_disk(audio_dir: Path):
    content = b"fake audio bytes"
    upload = make_upload_file(content=content, filename="sound.wav")

    filename = await audio_service.save_audio(upload)

    assert (audio_dir / filename).read_bytes() == content


async def test_save_audio_generates_unique_filenames(audio_dir: Path):
    upload_a = make_upload_file(filename="a.mp3")
    upload_b = make_upload_file(filename="a.mp3")

    filename_a = await audio_service.save_audio(upload_a)
    filename_b = await audio_service.save_audio(upload_b)

    assert filename_a != filename_b


async def test_save_audio_none_filename_uses_bin_suffix(audio_dir: Path):
    upload = make_upload_file()
    upload.filename = None

    filename = await audio_service.save_audio(upload)

    assert filename.endswith(".bin")


async def test_save_audio_empty_filename_uses_bin_suffix(audio_dir: Path):
    upload = make_upload_file(filename="")

    filename = await audio_service.save_audio(upload)

    assert filename.endswith(".bin")


async def test_save_audio_disallowed_extension_uses_bin_suffix(audio_dir: Path):
    """Unsupported extensions (e.g. .html, .exe) are replaced with .bin to prevent XSS."""
    upload = make_upload_file(filename="malicious.html")

    filename = await audio_service.save_audio(upload)

    assert filename.endswith(".bin")


async def test_delete_audio_removes_existing_file(audio_dir: Path):
    filepath = audio_dir / "clip.mp3"
    filepath.write_bytes(b"data")

    await audio_service.delete_audio("clip.mp3")

    assert not filepath.exists()


async def test_delete_audio_nonexistent_file_does_not_raise(audio_dir: Path):
    await audio_service.delete_audio("ghost.mp3")


async def test_delete_audio_rejects_path_traversal(audio_dir: Path):
    """Path traversal (e.g. ../../../etc/passwd) raises ValueError."""
    with pytest.raises(ValueError, match="path traversal"):
        await audio_service.delete_audio("../../../etc/passwd")
