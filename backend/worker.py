import asyncio
import json
import logging
import os
import tempfile

import httpx
from arq.connections import RedisSettings

from config.gemini import GeminiClient
from config.langfuse import LangfuseClient
from config.settings import settings
from models.handTracking import HandTracker
from services.collector import collector
from services.inference import InferenceService
from services.storage import save_bytes

logger = logging.getLogger(__name__)


async def process_sign_video(ctx: dict, video_id: str, content_type: str) -> None:
    """Download video from SeaweedFS, run hand tracking + Gemini, store result in Redis."""
    redis = ctx["redis"]
    inference: InferenceService = ctx["inference"]

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

    # Write to temp file for OpenCV
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name
        loop = asyncio.get_running_loop()
        frame_b64, landmarks_found = await loop.run_in_executor(
            None, HandTracker.process_video, tmp_path, video_id
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    if not frame_b64:
        payload = {"status": "error", "detail": "No frames extracted from video"}
    else:
        sign = await inference.recognize_sign(frame_b64)
        payload = {
            "status": "done",
            "gloss": sign["gloss"],
            "english": sign["english"],
            "confidence": sign["confidence"],
            "landmarks_found": landmarks_found,
        }
        try:
            await collector.log_inference(
                video_id=video_id,
                gloss=sign["gloss"],
                english=sign["english"],
                confidence=sign["confidence"],
                landmarks_found=landmarks_found,
            )
        except Exception:
            logger.warning("collector.log_inference failed", exc_info=True)

    await redis.setex(f"sign:{video_id}", 3600, json.dumps(payload))
    logger.info("process_sign_video done: video_id=%s status=%s", video_id, payload["status"])


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
