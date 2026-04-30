import asyncio
import json
import logging
import os
import tempfile
import uuid
from pathlib import Path
from typing import Annotated

import httpx
from fastapi import APIRouter, BackgroundTasks, File, Header, HTTPException, UploadFile
from fastapi.responses import Response
from arq import create_pool
from arq.connections import RedisSettings

_TMP_VIDEOS = Path("/app/tmp_videos")

from config.redis import RedisClient
from config.settings import settings
from schemas.sign import (
    CorrectionRequest,
    CorrectionResponse,
    CorrectionsListResponse,
    QueuedResponse,
    SignResultResponse,
)
from services import storage
from services.collector import collector

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/sign", tags=["sign"])

_CORRECTIONS_FILE = Path(__file__).parent.parent / "data" / "raw" / "corrections.jsonl"


async def _get_arq():
    return await create_pool(RedisSettings.from_dsn(settings.redis_url))


@router.post("/recognize", status_code=202)
async def recognize(
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File()],
    x_session_id: Annotated[str | None, Header()] = None,
) -> QueuedResponse:
    valid, reason = await storage.validate(file)
    if not valid:
        raise HTTPException(status_code=400, detail=reason)

    video_id = str(uuid.uuid4())
    session_id = x_session_id or str(uuid.uuid4())
    content_type = file.content_type or "video/mp4"
    contents = await file.read()

    # Write to shared volume immediately so worker can start without downloading
    _TMP_VIDEOS.mkdir(parents=True, exist_ok=True)
    ext = ".mov" if content_type == "video/quicktime" else ".mp4"
    tmp_path = str(_TMP_VIDEOS / f"{video_id}{ext}")
    await asyncio.to_thread(Path(tmp_path).write_bytes, contents)
    logger.info("recognize: saved %d bytes to %s", len(contents), tmp_path)

    # SeaweedFS upload runs in the background — doesn't block the response
    async def _save_to_seaweed():
        try:
            await storage.save_bytes(contents, video_id, content_type)
        except Exception:
            logger.warning("SeaweedFS background save failed for video_id=%s", video_id, exc_info=True)

    background_tasks.add_task(_save_to_seaweed)

    await RedisClient.client().setex(
        f"sign:{video_id}", 3600, json.dumps({"status": "processing"})
    )

    arq = await _get_arq()
    await arq.enqueue_job("process_sign_video", video_id, content_type, session_id, tmp_path)
    await arq.aclose()

    return QueuedResponse(video_id=video_id)


@router.post("/detect-hands")
async def detect_hands(file: Annotated[UploadFile, File()]) -> dict:
    """Quick MediaPipe pre-flight: returns whether at least one sampled frame contains a hand.

    Used by the frontend after recording but before submitting to Gemini, so the user can
    retake instead of paying the inference cost on a clip with no visible hands.
    """
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="empty file")

    content_type = file.content_type or "video/mp4"
    suffix = ".mov" if content_type == "video/quicktime" else ".mp4"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        from models.handTracking import HandTracker
        loop = asyncio.get_running_loop()
        detected = await loop.run_in_executor(None, HandTracker.quick_detect, tmp_path)
        return {"hands_detected": bool(detected)}
    except Exception:
        logger.exception("detect_hands failed")
        raise HTTPException(status_code=500, detail="detection failed")
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


@router.get("/result/{video_id}")
async def get_result(video_id: str) -> SignResultResponse:
    data = await RedisClient.client().get(f"sign:{video_id}")
    if not data:
        raise HTTPException(status_code=404, detail="video_id not found or expired")
    return SignResultResponse(video_id=video_id, **json.loads(data))


@router.get("/audio/{video_id}")
async def get_audio(video_id: str):
    """Proxy TTS audio from SeaweedFS so the frontend can reach it."""
    url = f"{settings.seaweedfs_filer_url}/audio/{video_id}.mp3"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10)
            if resp.status_code == 404:
                raise HTTPException(status_code=404, detail="Audio not found")
            resp.raise_for_status()
            return Response(content=resp.content, media_type="audio/mpeg")
    except HTTPException:
        raise
    except Exception:
        logger.error("Audio proxy failed for video_id=%s", video_id, exc_info=True)
        raise HTTPException(status_code=502, detail="Audio unavailable")


@router.post("/corrections")
async def create_correction(body: CorrectionRequest) -> CorrectionResponse:
    correction_id = await collector.log_correction(
        video_id=body.video_id,
        correct_gloss=body.correct_gloss,
        notes=body.notes,
    )
    return CorrectionResponse(id=correction_id)


@router.get("/corrections")
async def list_corrections() -> CorrectionsListResponse:
    if not _CORRECTIONS_FILE.exists():
        return CorrectionsListResponse(total=0, recent=[])
    records: list[dict] = []
    try:
        for line in _CORRECTIONS_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                records.append(json.loads(line))
    except Exception:
        logger.warning("Could not read corrections file", exc_info=True)
        return CorrectionsListResponse(total=0, recent=[])
    return CorrectionsListResponse(total=len(records), recent=records[-20:])
