import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from routers.conversations import router
from schemas.conversation import ConversationMessagesResponse

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_get_messages_unknown_session_returns_empty():
    session_id = str(uuid.uuid4())
    with patch("routers.conversations.Database") as mock_db:
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_result_conv = MagicMock()
        mock_result_conv.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result_conv)
        mock_db.Session.return_value = mock_session

        response = client.get(f"/api/v1/conversations/{session_id}/messages")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["messages"] == []
