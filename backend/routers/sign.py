from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/sign", tags=["sign"])

@router.post("/recognize")
async def recognize():
    return {"api_version": "v1", "message": "not implemented"}

@router.post("/corrections")
async def create_correction():
    return {"api_version": "v1", "message": "not implemented"}

@router.get("/corrections")
async def list_corrections():
    return {"api_version": "v1", "message": "not implemented"}
