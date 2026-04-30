import asyncio
import json
import logging
import os
import subprocess
import tempfile
import uuid

import httpx
from arq.connections import RedisSettings

from config.database import Database
from config.elevenlabs import ElevenLabsClient
from config.gemini import GeminiClient
from config.langfuse import LangfuseClient
from config.settings import settings
from models.handTracking import FaceTracker, HandTracker
from services.collector import collector
from services.conversation import insert_message, upsert_conversation
from services.inference import InferenceService, _DEMO_HARDCODE as _INFERENCE_DEMO_MODE
from services.speech import SpeechService
from services.storage import save_bytes

logger = logging.getLogger(__name__)


def _transcode_to_480p(src: str) -> str:
    """Convert any video to 480p H.264 mp4. Returns path to new file (caller must delete)."""
    dst = src.rsplit(".", 1)[0] + "_480p.mp4"
    cmd = [
        "ffmpeg", "-y", "-i", src,
        "-vf", "scale=-2:480",
        "-c:v", "libx264", "-crf", "28", "-preset", "ultrafast",
        "-c:a", "aac", "-b:a", "64k",
        "-movflags", "+faststart",
        dst,
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr.decode()[:200]}")
    return dst


async def process_sign_video(ctx: dict, video_id: str, content_type: str, session_id: str | None = None) -> None:
    redis = ctx["redis"]
    inference: InferenceService = ctx["inference"]
    speech: SpeechService = ctx["speech"]
    db_session = ctx["db_session"]

    try:
        sign = None
        landmarks_found = False

        if _INFERENCE_DEMO_MODE:
            sign = await inference.recognize_sign("", [], mime_type="video/mp4")
            landmarks_found = True
        else:
            tmp_path = None
            compressed_path = None
            try:
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
                ext = ".mov" if content_type == "video/quicktime" else ".mp4"
                with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                    tmp.write(contents)
                    tmp_path = tmp.name

                loop = asyncio.get_running_loop()
                try:
                    compressed_path = await loop.run_in_executor(None, _transcode_to_480p, tmp_path)
                except Exception:
                    logger.warning("ffmpeg transcode failed, using original", exc_info=True)
                    compressed_path = tmp_path

                # MediaPipe must finish before Gemini so we can pass velocity vectors —
                # essential for distinguishing motion-modified signs (9 vs 19, COME vs GO).
                landmark_sequence, landmarks_found = await loop.run_in_executor(
                    None, HandTracker.process_video, compressed_path, video_id,
                )

                sign = await inference.recognize_sign(
                    compressed_path, landmark_sequence, mime_type="video/mp4",
                )

            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                if compressed_path and compressed_path != tmp_path and os.path.exists(compressed_path):
                    os.unlink(compressed_path)

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
            "landmarks_found": landmarks_found,
            "audio_url": audio_url,
        }
        try:
            await collector.log_inference(
                video_id=video_id,
                gloss=gloss,
                english=english,
                confidence=confidence,
                landmarks_found=landmarks_found,
            )
        except Exception:
            logger.warning("collector.log_inference failed", exc_info=True)

        await redis.setex(f"sign:{video_id}", 3600, json.dumps(payload))
    except Exception:
        logger.exception("process_sign_video crashed for video_id=%s", video_id)
        await redis.setex(
            f"sign:{video_id}",
            3600,
            json.dumps({"status": "error", "detail": "Internal worker error during sign processing"}),
        )


async def startup(ctx: dict) -> None:
    import logging as _logging
    from pythonjsonlogger import jsonlogger
    handler = _logging.StreamHandler()
    handler.setFormatter(jsonlogger.JsonFormatter(fmt="%(asctime)s %(name)s %(levelname)s %(message)s"))
    _logging.getLogger().setLevel(_logging.INFO)
    _logging.getLogger().handlers = [handler]

    HandTracker.load()
    FaceTracker.load()
    gemini = GeminiClient.connect()
    langfuse = LangfuseClient.connect()
    ctx["inference"] = InferenceService(gemini=gemini, langfuse=langfuse)
    elevenlabs = ElevenLabsClient.connect()
    ctx["speech"] = SpeechService(elevenlabs=elevenlabs, voice_id=settings.elevenlabs_voice_id)
    ctx["db_session"] = Database.Session
    logger.info("ARQ worker started")


async def shutdown(ctx: dict) -> None:
    HandTracker.unload()
    FaceTracker.unload()
    logger.info("ARQ worker stopped")


class WorkerSettings:
    functions = [process_sign_video]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 2
    job_timeout = 120
    keep_result = 3600
