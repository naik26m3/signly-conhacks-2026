from datetime import datetime
from pydantic import BaseModel


class MessageItem(BaseModel):
    id: str
    direction: str
    content: str
    gloss: str | None = None
    audio_url: str | None = None
    confidence: float | None = None
    created_at: datetime


class ConversationMessagesResponse(BaseModel):
    api_version: str = "v1"
    conversation_id: str
    total: int
    messages: list[MessageItem]


class ConversationTitleResponse(BaseModel):
    api_version: str = "v1"
    title: str
