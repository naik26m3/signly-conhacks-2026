import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
sys.path.insert(0, "/home/dat/Documents/signly-conhacks-2026/backend")


def _make_inference_service():
    from services.inference import InferenceService
    mock_gemini = MagicMock()
    return InferenceService(gemini=mock_gemini), mock_gemini


@pytest.mark.asyncio
async def test_recognize_sign_uploads_and_deletes_file():
    """recognize_sign uploads video to Files API and deletes it after."""
    service, mock_gemini = _make_inference_service()

    mock_uploaded = MagicMock()
    mock_uploaded.name = "files/abc123"
    mock_uploaded.uri = "https://generativelanguage.googleapis.com/v1beta/files/abc123"

    mock_gemini.aio.files.upload = AsyncMock(return_value=mock_uploaded)
    mock_gemini.aio.files.delete = AsyncMock()

    mock_response = MagicMock()
    mock_response.text = '{"gloss": "HELLO", "english": "Hello", "confidence": 0.9}'
    mock_gemini.aio.models.generate_content = AsyncMock(return_value=mock_response)

    landmark_sequence = [{"frame": 0, "right": [[0.1, 0.2, 0.0]] * 21}]
    result = await service.recognize_sign("/tmp/test.mp4", landmark_sequence)

    mock_gemini.aio.files.upload.assert_called_once()
    mock_gemini.aio.files.delete.assert_called_once_with(name="files/abc123")

    assert result["gloss"] == "HELLO"
    assert result["english"] == "Hello"
    assert result["confidence"] == 0.9


@pytest.mark.asyncio
async def test_recognize_sign_includes_landmarks_in_prompt():
    """Landmark JSON is included in the generate_content call."""
    service, mock_gemini = _make_inference_service()

    mock_uploaded = MagicMock()
    mock_uploaded.name = "files/xyz"
    mock_uploaded.uri = "https://example.com/file"

    mock_gemini.aio.files.upload = AsyncMock(return_value=mock_uploaded)
    mock_gemini.aio.files.delete = AsyncMock()

    mock_response = MagicMock()
    mock_response.text = '{"gloss": "THANK_YOU", "english": "Thank you", "confidence": 0.85}'
    mock_gemini.aio.models.generate_content = AsyncMock(return_value=mock_response)

    landmark_sequence = [{"frame": 0, "right": [[0.5, 0.5, 0.0]] * 21}]
    await service.recognize_sign("/tmp/test.mp4", landmark_sequence)

    generate_call = mock_gemini.aio.models.generate_content.call_args
    contents = (
        generate_call.kwargs.get("contents")
        or (generate_call[1].get("contents") if generate_call[1] else None)
        or (generate_call[0][0] if generate_call[0] else None)
    )
    prompt_text = str(contents)
    assert "frame" in prompt_text


@pytest.mark.asyncio
async def test_recognize_sign_deletes_file_even_on_gemini_error():
    """Gemini file is always deleted, even if generate_content raises."""
    service, mock_gemini = _make_inference_service()

    mock_uploaded = MagicMock()
    mock_uploaded.name = "files/abc"
    mock_uploaded.uri = "https://example.com/file"

    mock_gemini.aio.files.upload = AsyncMock(return_value=mock_uploaded)
    mock_gemini.aio.files.delete = AsyncMock()
    mock_gemini.aio.models.generate_content = AsyncMock(side_effect=RuntimeError("Gemini unavailable"))

    landmark_sequence = [{"frame": 0, "right": [[0.1, 0.2, 0.0]] * 21}]
    result = await service.recognize_sign("/tmp/test.mp4", landmark_sequence)

    mock_gemini.aio.files.delete.assert_called_once_with(name="files/abc")
    assert result["gloss"] == "UNKNOWN"


@pytest.mark.asyncio
async def test_recognize_sign_returns_no_key_when_gemini_not_configured():
    """Returns NO_KEY dict when Gemini client is None."""
    from services.inference import InferenceService
    service = InferenceService(gemini=None)
    result = await service.recognize_sign("/tmp/test.mp4", [])
    assert result["gloss"] == "NO_KEY"
