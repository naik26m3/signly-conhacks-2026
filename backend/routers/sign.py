import asyncio
import json
import logging
import os
import tempfile
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from config.redis import RedisClient
from models.handTracking import HandTracker
from services import inference, storage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/sign", tags=["sign"])


@router.post("/recognize")
async def recognize(file: UploadFile = File(...)):
    valid, reason = await storage.validate(file)
    if not valid:
        raise HTTPException(status_code=400, detail=reason)

    video_id = str(uuid.uuid4())
    contents = await file.read()

    # Write to temp file so OpenCV can read it
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        loop = asyncio.get_event_loop()
        frame_b64, landmarks_found = await loop.run_in_executor(
            None, HandTracker.process_video, tmp_path, video_id
        )
    finally:
        os.unlink(tmp_path)

    if not frame_b64:
        raise HTTPException(status_code=422, detail="Could not extract any frames from video")

    # Send best frame to Gemini
    result = await inference.recognize_sign(frame_b64)

    # Save original video to SeaweedFS for dataset logging (best-effort)
    try:
        await storage.save_bytes(contents, video_id, file.content_type or "video/mp4")
    except Exception:
        logger.warning("SeaweedFS save failed — continuing without storage", exc_info=True)

    # Cache result in Redis
    await RedisClient.client().setex(
        f"sign:{video_id}",
        3600,
        json.dumps({**result, "video_id": video_id, "landmarks_found": landmarks_found}),
    )

    return {
        "api_version": "v1",
        "video_id": video_id,
        "gloss": result["gloss"],
        "english": result["english"],
        "confidence": result["confidence"],
        "landmarks_found": landmarks_found,
    }


@router.post("/corrections")
async def create_correction():
    return {"api_version": "v1", "message": "not implemented"}


@router.get("/corrections")
async def list_corrections():
    return {"api_version": "v1", "message": "not implemented"}
