from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["health"])

@router.get("/health")
async def health():
    return {"api_version": "v1", "status": "ok"}
