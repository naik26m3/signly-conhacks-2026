import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_upsert_conversation_creates_new():
    from services.conversation import upsert_conversation
    session_id = uuid.uuid4()

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()

    conv = await upsert_conversation(mock_session, session_id)

    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()
    assert conv.session_id == session_id


@pytest.mark.asyncio
async def test_upsert_conversation_returns_existing():
    from services.conversation import upsert_conversation
    import uuid
    from db.models import Conversation

    session_id = uuid.uuid4()
    existing = Conversation(session_id=session_id)

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing
    mock_session.execute = AsyncMock(return_value=mock_result)

    conv = await upsert_conversation(mock_session, session_id)

    mock_session.add.assert_not_called()
    assert conv is existing


@pytest.mark.asyncio
async def test_insert_message():
    from services.conversation import insert_message
    import uuid

    conv_id = uuid.uuid4()
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()

    msg = await insert_message(
        mock_session,
        conversation_id=conv_id,
        direction="deaf_to_hearing",
        content="Hello",
        gloss="HELLO",
        audio_url="http://filer/audio/abc.mp3",
        confidence=0.92,
    )

    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()
    assert msg.direction == "deaf_to_hearing"
    assert msg.content == "Hello"
    assert msg.audio_url == "http://filer/audio/abc.mp3"
