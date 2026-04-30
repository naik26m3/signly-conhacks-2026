import asyncio
import json
import logging
import os
import subprocess
import tempfile
import uuid
from pathlib import Path

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
from services.inference import InferenceService
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


def _export_gemini_view(src: str, dst: str, fps: float = 2.0) -> bool:
    """Build a stop-motion video containing only the frames Gemini samples.

    Each frame is held visible for 1/fps seconds — lets the user actually see
    what motion (or lack thereof) Gemini perceives at the configured sampling rate.
    """
    cmd = [
        "ffmpeg", "-y", "-i", src,
        "-vf", f"fps={fps}",
        "-r", str(fps),
        "-c:v", "libx264", "-crf", "28", "-preset", "ultrafast",
        "-an",
        dst,
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=15)
    if result.returncode != 0:
        logger.warning("ffmpeg gemini-view export failed: %s", result.stderr.decode()[:200])
        return False
    return True


async def process_sign_video(ctx: dict, video_id: str, content_type: str, session_id: str | None = None, shared_tmp_path: str | None = None) -> None:
    """Process sign video: use shared tmp if available, else download from SeaweedFS."""
    redis = ctx["redis"]
    inference: InferenceService = ctx["inference"]
    speech: SpeechService = ctx["speech"]
    db_session = ctx["db_session"]

    try:
        # Hand tracking + Gemini (tmp file must stay alive through recognize_sign)
        tmp_path = None
        compressed_path = None
        own_tmp = False
        sign = None
        try:
            if shared_tmp_path and os.path.exists(shared_tmp_path):
                # Fast path: use file written directly by API — no SeaweedFS round trip
                tmp_path = shared_tmp_path
                logger.info("process_sign_video: using shared tmp %s (skipped SeaweedFS download)", tmp_path)
            else:
                # Fallback: download from SeaweedFS
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
                own_tmp = True

            # Transcode to 480p mp4 — faster Gemini upload and smaller inline payload
            loop = asyncio.get_running_loop()
            try:
                compressed_path = await loop.run_in_executor(None, _transcode_to_480p, tmp_path)
                logger.info(
                    "process_sign_video: transcoded %s → %s (%.1f MB)",
                    tmp_path, compressed_path,
                    os.path.getsize(compressed_path) / 1024 / 1024,
                )
            except Exception:
                logger.warning("ffmpeg transcode failed, using original", exc_info=True)
                compressed_path = tmp_path

            # Export a stop-motion view of exactly the frames Gemini samples (best-effort).
            # Lands at /debug/videos/<video_id>_gemini_view.mp4 — host path: ./debug/videos/.
            try:
                gemini_view_path = f"/debug/videos/{video_id}_gemini_view.mp4"
                Path(gemini_view_path).parent.mkdir(parents=True, exist_ok=True)
                ok = await loop.run_in_executor(
                    None, _export_gemini_view, compressed_path, gemini_view_path, 2.0,
                )
                if ok:
                    logger.info("Gemini-view stop-motion saved → %s", gemini_view_path)
            except Exception:
                logger.warning("gemini-view export failed", exc_info=True)

            # MediaPipe must finish before Gemini so we can pass velocity vectors —
            # essential for distinguishing motion-modified signs (9 vs 19, COME vs GO).
            # We pay ~5s of serialization here in exchange for accurate motion disambiguation.
            landmark_sequence, landmarks_found = await loop.run_in_executor(
                None, HandTracker.process_video, compressed_path, video_id,
            )
            if not landmarks_found:
                logger.info("process_sign_video: no hands detected for video_id=%s", video_id)
                # Don't abort — Gemini can still infer from raw video alone

            sign = await inference.recognize_sign(
                compressed_path, landmark_sequence, mime_type="video/mp4", debug_id=video_id,
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
        logger.info("process_sign_video done: video_id=%s gloss=%s audio_url=%s", video_id, gloss, audio_url)
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
