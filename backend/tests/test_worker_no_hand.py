import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
sys.path.insert(0, "/home/dat/Documents/signly-conhacks-2026/backend")
sys.path.insert(0, "/home/dat/Documents/signly-conhacks-2026")


@pytest.mark.asyncio
async def test_no_hand_writes_no_hand_result_and_skips_gemini():
    """When no hands detected, Redis gets NO_HAND and inference is never called."""
    mock_redis = AsyncMock()
    mock_inference = AsyncMock()
    mock_inference.recognize_sign = AsyncMock()

    ctx = {
        "redis": mock_redis,
        "inference": mock_inference,
        "speech": AsyncMock(),
        "db_session": MagicMock(),
    }

    with patch("worker.httpx.AsyncClient") as mock_http, \
         patch("worker.HandTracker.process_video", return_value=([], False)), \
         patch("worker.tempfile.NamedTemporaryFile") as mock_tmp, \
         patch("worker.os.path.exists", return_value=True), \
         patch("worker.os.unlink"):

        mock_resp = AsyncMock()
        mock_resp.content = b"fake-video"
        mock_resp.raise_for_status = MagicMock()
        mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_http.return_value)
        mock_http.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_http.return_value.get = AsyncMock(return_value=mock_resp)

        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_file.name = "/tmp/fake.mp4"
        mock_file.write = MagicMock()
        mock_tmp.return_value = mock_file

        from worker import process_sign_video
        await process_sign_video(ctx, "video123", "video/mp4", "session-uuid")

    mock_redis.setex.assert_called_once()
    call_args = mock_redis.setex.call_args[0]
    payload = json.loads(call_args[2])
    assert payload["status"] == "done"
    assert payload["gloss"] == "NO_HAND"
    assert payload["english"] == "No hand detected — try again"
    assert payload["confidence"] == 0.0

    mock_inference.recognize_sign.assert_not_called()


@pytest.mark.asyncio
async def test_normal_path_calls_recognize_sign_with_tmp_path():
    """When hands found, recognize_sign is called with the tmp file path."""
    landmark_sequence = [{"frame": 0, "right": [[0.1, 0.2, 0.0]] * 21}]

    mock_redis = AsyncMock()
    mock_inference = MagicMock()
    mock_inference.recognize_sign = AsyncMock(return_value={
        "gloss": "HELLO", "english": "Hello", "confidence": 0.9
    })

    mock_speech = MagicMock()
    mock_speech.synthesize = AsyncMock(return_value=b"")

    mock_db_session = MagicMock()
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session.begin = MagicMock(return_value=mock_session)
    mock_db_session.return_value = mock_session

    ctx = {
        "redis": mock_redis,
        "inference": mock_inference,
        "speech": mock_speech,
        "db_session": mock_db_session,
    }

    with patch("worker.httpx.AsyncClient") as mock_http, \
         patch("worker.HandTracker.process_video", return_value=(landmark_sequence, True)), \
         patch("worker.tempfile.NamedTemporaryFile") as mock_tmp, \
         patch("worker.os.path.exists", return_value=True), \
         patch("worker.os.unlink"), \
         patch("worker.collector.log_inference", new=AsyncMock()), \
         patch("worker.upsert_conversation", new=AsyncMock(return_value=MagicMock(id="conv-id"))), \
         patch("worker.insert_message", new=AsyncMock()):

        mock_resp = AsyncMock()
        mock_resp.content = b"fake-video"
        mock_resp.raise_for_status = MagicMock()
        mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_http.return_value)
        mock_http.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_http.return_value.get = AsyncMock(return_value=mock_resp)

        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_file.name = "/tmp/fake.mp4"
        mock_file.write = MagicMock()
        mock_tmp.return_value = mock_file

        from worker import process_sign_video
        await process_sign_video(ctx, "video123", "video/mp4", "session-uuid")

    mock_inference.recognize_sign.assert_called_once_with("/tmp/fake.mp4", landmark_sequence)
