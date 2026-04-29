from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/speech", tags=["speech"])

@router.post("/transcribe")
async def transcribe():
    return {"api_version": "v1", "message": "not implemented"}
