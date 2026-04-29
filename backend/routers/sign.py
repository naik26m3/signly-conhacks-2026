import json
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from arq import create_pool
from arq.connections import RedisSettings

from config.redis import RedisClient
from config.settings import settings
from schemas.sign import CorrectionRequest, CorrectionResponse, CorrectionsListResponse
from services import storage
from services.collector import collector

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/sign", tags=["sign"])

_CORRECTIONS_FILE = Path(__file__).parent.parent / "data" / "raw" / "corrections.jsonl"


async def _get_arq():
    return await create_pool(RedisSettings.from_dsn(settings.redis_url))


@router.post("/recognize", status_code=202)
async def recognize(file: UploadFile = File(...)):
    valid, reason = await storage.validate(file)
    if not valid:
        raise HTTPException(status_code=400, detail=reason)

    video_id = str(uuid.uuid4())
    contents = await file.read()

    # Save video to SeaweedFS first — worker will download it
    try:
        await storage.save_bytes(contents, video_id, file.content_type or "video/mp4")
    except Exception:
        logger.error("SeaweedFS save failed for video_id=%s", video_id, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to store video")

    # Mark as queued in Redis
    await RedisClient.client().setex(
        f"sign:{video_id}", 3600, json.dumps({"status": "processing"})
    )

    # Enqueue ARQ job
    arq = await _get_arq()
    await arq.enqueue_job("process_sign_video", video_id, file.content_type or "video/mp4")
    await arq.aclose()

    return {"api_version": "v1", "video_id": video_id, "status": "processing"}


@router.get("/result/{video_id}")
async def get_result(video_id: str):
    data = await RedisClient.client().get(f"sign:{video_id}")
    if not data:
        raise HTTPException(status_code=404, detail="video_id not found or expired")
    return {"api_version": "v1", "video_id": video_id, **json.loads(data)}


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
