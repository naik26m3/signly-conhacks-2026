import asyncio
import json
import logging
import os
import tempfile
import uuid

import httpx
from arq.connections import RedisSettings

from config.database import Database
from config.elevenlabs import ElevenLabsClient
from config.gemini import GeminiClient
from config.langfuse import LangfuseClient
from config.settings import settings
from models.handTracking import HandTracker
from services.collector import collector
from services.conversation import insert_message, upsert_conversation
from services.inference import InferenceService
from services.speech import SpeechService
from services.storage import save_bytes

logger = logging.getLogger(__name__)


async def process_sign_video(ctx: dict, video_id: str, content_type: str, session_id: str | None = None) -> None:
    """Download video from SeaweedFS, run hand tracking + Gemini, store result in Redis."""
    redis = ctx["redis"]
    inference: InferenceService = ctx["inference"]
    speech: SpeechService = ctx["speech"]
    db_session = ctx["db_session"]

    # Download video from SeaweedFS
    url = f"{settings.seaweedfs_filer_url}/videos/{video_id}.mp4"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            resp.raise_for_status()
            contents = resp.content
    except Exception:
        logger.error("Failed to download video %s from SeaweedFS", video_id, exc_info=True)
        await redis.setex(f"sign:{video_id}", 3600, json.dumps({"status": "error", "detail": "Could not retrieve video"}))
        return

    # Hand tracking + Gemini (tmp file must stay alive through recognize_sign)
    tmp_path = None
    sign = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        loop = asyncio.get_running_loop()
        landmark_sequence, landmarks_found = await loop.run_in_executor(
            None, HandTracker.process_video, tmp_path, video_id
        )

        if not landmarks_found:
            await redis.setex(f"sign:{video_id}", 3600, json.dumps({
                "status": "done",
                "gloss": "NO_HAND",
                "english": "No hand detected — try again",
                "confidence": 0.0,
                "landmarks_found": False,
                "audio_url": None,
            }))
            logger.info("process_sign_video: no hands detected for video_id=%s", video_id)
            return

        sign = await inference.recognize_sign(tmp_path, landmark_sequence)

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    if sign is None:
        await redis.setex(f"sign:{video_id}", 3600, json.dumps({"status": "error", "detail": "Recognition failed"}))
        return

    gloss = sign["gloss"]
    english = sign["english"]
    confidence = sign["confidence"]

    # TTS: synthesise audio and save to SeaweedFS
    audio_url: str | None = None
    try:
        audio_bytes = await speech.synthesize(english)
        if audio_bytes:
            result = await save_bytes(audio_bytes, video_id, "audio/mpeg", folder="audio", ext="mp3")
            audio_url = result["url"]
    except Exception:
        logger.warning("TTS or audio save failed for video_id=%s", video_id, exc_info=True)

    # Persist conversation + message
    try:
        sid = uuid.UUID(session_id) if session_id else uuid.uuid4()
        async with db_session() as session:
            async with session.begin():
                conv = await upsert_conversation(session, sid)
                await insert_message(
                    session,
                    conversation_id=conv.id,
                    direction="deaf_to_hearing",
                    content=english,
                    gloss=gloss,
                    audio_url=audio_url,
                    confidence=confidence,
                )
    except Exception:
        logger.warning("DB insert failed for video_id=%s", video_id, exc_info=True)

    payload = {
        "status": "done",
        "gloss": gloss,
        "english": english,
        "confidence": confidence,
        "landmarks_found": True,
        "audio_url": audio_url,
    }
    try:
        await collector.log_inference(
            video_id=video_id,
            gloss=gloss,
            english=english,
            confidence=confidence,
            landmarks_found=True,
        )
    except Exception:
        logger.warning("collector.log_inference failed", exc_info=True)

    await redis.setex(f"sign:{video_id}", 3600, json.dumps(payload))
    logger.info("process_sign_video done: video_id=%s gloss=%s audio_url=%s", video_id, gloss, audio_url)


async def startup(ctx: dict) -> None:
    import logging as _logging
    from pythonjsonlogger import jsonlogger
    handler = _logging.StreamHandler()
    handler.setFormatter(jsonlogger.JsonFormatter(fmt="%(asctime)s %(name)s %(levelname)s %(message)s"))
    _logging.getLogger().setLevel(_logging.INFO)
    _logging.getLogger().handlers = [handler]

    HandTracker.load()
    gemini = GeminiClient.connect()
    langfuse = LangfuseClient.connect()
    ctx["inference"] = InferenceService(gemini=gemini, langfuse=langfuse)
    elevenlabs = ElevenLabsClient.connect()
    ctx["speech"] = SpeechService(elevenlabs=elevenlabs)
    ctx["db_session"] = Database.Session
    logger.info("ARQ worker started")


async def shutdown(ctx: dict) -> None:
    HandTracker.unload()
    logger.info("ARQ worker stopped")


class WorkerSettings:
    functions = [process_sign_video]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 2
    job_timeout = 120
    keep_result = 3600
