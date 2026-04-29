import logging

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from schemas.speech import TranscribeResponse

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
async def transcribe(request: Request, file: UploadFile = File(...)) -> TranscribeResponse:
    """Transcribe uploaded audio to text and convert the transcript to ASL gloss.

    Accepts m4a / mp4 / mpeg / wav / webm audio. Returns both the English
    transcript produced by ElevenLabs Scribe and the ASL gloss produced by
    Gemini.
    """
    if file.content_type not in _ALLOWED_AUDIO_TYPES:
        raise HTTPException(status_code=400, detail=f"unsupported audio format: {file.content_type}")

    contents = await file.read()
    logger.info("transcribe endpoint: %d bytes, content_type=%s", len(contents), file.content_type)

    transcript = await request.app.state.speech.transcribe(contents, file.content_type or "audio/m4a")
    gloss = await request.app.state.inference.english_to_gloss(transcript) if transcript else ""

    return TranscribeResponse(transcript=transcript, gloss=gloss)
