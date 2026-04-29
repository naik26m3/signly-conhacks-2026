import json
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from config.redis import RedisClient
from services.storage import validate, save

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/uploads", tags=["uploads"])

@router.post("/video")
async def upload_video(file: UploadFile = File(...)):
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
        f"upload:{result['video_id']}",
        3600,
        json.dumps({"url": result["url"], "status": "ready"}),
    )

    return {
        "api_version": "v1",
        "video_id": result["video_id"],
        "status": "ready",
    }

@router.post("/text")
async def upload_text():
    return {"api_version": "v1", "message": "not implemented"}
