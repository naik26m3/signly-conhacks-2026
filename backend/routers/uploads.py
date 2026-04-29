from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/uploads", tags=["uploads"])

@router.post("/video")
async def upload_video():
    return {"api_version": "v1", "message": "not implemented"}

@router.post("/text")
async def upload_text():
    return {"api_version": "v1", "message": "not implemented"}
