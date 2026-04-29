import json
import logging
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile

from config.redis import RedisClient
from schemas.upload import UploadTextResponse, UploadVideoResponse
from services.storage import validate, save

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/uploads", tags=["uploads"])


@router.post("/video")
async def upload_video(file: Annotated[UploadFile, File()]) -> UploadVideoResponse:
    valid, reason = await validate(file)
    if not valid:
        raise HTTPException(status_code=400, detail=reason)

    try:
        result = await save(file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("failed to save video to seaweedfs")
        raise HTTPException(status_code=500, detail="upload failed")

    await RedisClient.client().setex(
        f"upload:{result['file_id']}",
        3600,
        json.dumps({"url": result["url"], "status": "ready"}),
    )

    return UploadVideoResponse(video_id=result["file_id"])


@router.post("/text")
async def upload_text() -> UploadTextResponse:
    return UploadTextResponse(message="not implemented")
