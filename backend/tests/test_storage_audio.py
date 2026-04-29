import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_save_bytes_audio_path():
    file_id = "abc123"
    audio_bytes = b"fake-mp3-data"

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("services.storage.httpx.AsyncClient", return_value=mock_client), \
         patch("services.storage.settings") as mock_settings:
        mock_settings.seaweedfs_filer_url = "http://filer:8888"
        from services.storage import save_bytes
        result = await save_bytes(audio_bytes, file_id, "audio/mpeg", folder="audio", ext="mp3")

    assert result["url"] == "http://filer:8888/audio/abc123.mp3"
    assert result["file_id"] == "abc123"
    call_url = mock_client.post.call_args[0][0]
    assert "/audio/abc123.mp3" in call_url


@pytest.mark.asyncio
async def test_save_bytes_video_path():
    file_id = "vid999"
    video_bytes = b"fake-mp4-data"

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("services.storage.httpx.AsyncClient", return_value=mock_client), \
         patch("services.storage.settings") as mock_settings:
        mock_settings.seaweedfs_filer_url = "http://filer:8888"
        from services.storage import save_bytes
        result = await save_bytes(video_bytes, file_id, "video/mp4")

    assert result["url"] == "http://filer:8888/videos/vid999.mp4"
