import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, File, Header, HTTPException, Request, UploadFile

from config.database import Database
from schemas.speech import TranscribeResponse
from services.conversation import insert_message, upsert_conversation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/speech", tags=["speech"])

_ALLOWED_AUDIO_TYPES = {
    "audio/m4a",
    "audio/mp4",
    "audio/mpeg",
    "audio/wav",
    "audio/webm",
}


@router.post("/transcribe")
async def transcribe(
    request: Request,
    file: Annotated[UploadFile, File()],
    x_session_id: Annotated[str | None, Header()] = None,
) -> TranscribeResponse:
    if file.content_type not in _ALLOWED_AUDIO_TYPES:
        raise HTTPException(status_code=400, detail=f"unsupported audio format: {file.content_type}")

    contents = await file.read()
    logger.info("transcribe endpoint: %d bytes, content_type=%s", len(contents), file.content_type)

    transcript = await request.app.state.speech.transcribe(contents, file.content_type or "audio/m4a")
    gloss = await request.app.state.inference.english_to_gloss(transcript) if transcript else ""

    # Persist as hearing_to_deaf message
    if transcript:
        try:
            sid = uuid.UUID(x_session_id) if x_session_id else uuid.uuid4()
            async with Database.Session() as session:
                async with session.begin():
                    conv = await upsert_conversation(session, sid)
                    await insert_message(
                        session,
                        conversation_id=conv.id,
                        direction="hearing_to_deaf",
                        content=transcript,
                        gloss=gloss or None,
                    )
        except Exception:
            logger.warning("DB insert failed for speech transcription", exc_info=True)

    return TranscribeResponse(transcript=transcript, gloss=gloss)
