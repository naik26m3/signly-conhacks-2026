import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Conversation, Message

logger = logging.getLogger(__name__)


async def upsert_conversation(session: AsyncSession, session_id: uuid.UUID) -> Conversation:
    result = await session.execute(
        select(Conversation).where(Conversation.session_id == session_id)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing
    conv = Conversation(session_id=session_id)
    session.add(conv)
    await session.flush()
    return conv


async def insert_message(
    session: AsyncSession,
    *,
    conversation_id: uuid.UUID,
    direction: str,
    content: str,
    gloss: str | None = None,
    audio_url: str | None = None,
    confidence: float | None = None,
) -> Message:
    msg = Message(
        conversation_id=conversation_id,
        direction=direction,
        content=content,
        gloss=gloss,
        audio_url=audio_url,
        confidence=confidence,
    )
    session.add(msg)
    await session.flush()
    return msg
