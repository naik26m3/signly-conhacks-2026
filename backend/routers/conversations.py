import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Request
from sqlalchemy import select

from config.database import Database
from db.models import Conversation, Message
from schemas.conversation import (
    ConversationMessagesResponse,
    ConversationTitleResponse,
    MessageItem,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


@router.get("/{session_id}/messages")
async def get_messages(
    session_id: str,
    limit: Annotated[int, None] = 50,
) -> ConversationMessagesResponse:
    sid = uuid.UUID(session_id)
    async with Database.Session() as session:
        result = await session.execute(
            select(Conversation).where(Conversation.session_id == sid)
        )
        conv = result.scalar_one_or_none()
        if not conv:
            return ConversationMessagesResponse(
                conversation_id=session_id, total=0, messages=[]
            )

        msg_result = await session.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        messages = msg_result.scalars().all()

    items = [
        MessageItem(
            id=str(m.id),
            direction=m.direction,
            content=m.content,
            gloss=m.gloss,
            audio_url=m.audio_url,
            confidence=m.confidence,
            created_at=m.created_at,
        )
        for m in messages
    ]
    return ConversationMessagesResponse(
        conversation_id=str(conv.id),
        total=len(items),
        messages=items,
    )


@router.get("/{session_id}/title")
async def get_title(request: Request, session_id: str) -> ConversationTitleResponse:
    """Generate a 1-3 word topic label for the current session's conversation.

    Not cached on the DB — generation is cheap and conversations are short. If
    Gemini fails or there are no messages yet, returns an empty string and the
    frontend falls back to the default header.
    """
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        return ConversationTitleResponse(title="")

    async with Database.Session() as session:
        result = await session.execute(
            select(Conversation).where(Conversation.session_id == sid)
        )
        conv = result.scalar_one_or_none()
        if not conv:
            return ConversationTitleResponse(title="")

        msg_result = await session.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at.asc())
            .limit(20)
        )
        messages = msg_result.scalars().all()

    lines: list[str] = []
    for m in messages:
        speaker = "Signer" if m.direction == "deaf_to_hearing" else "Speaker"
        if m.content:
            lines.append(f"{speaker}: {m.content}")

    if not lines:
        return ConversationTitleResponse(title="")

    title = await request.app.state.inference.generate_title(lines)
    return ConversationTitleResponse(title=title)
