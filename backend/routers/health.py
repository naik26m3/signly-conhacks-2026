from fastapi import APIRouter

from schemas.health import HealthResponse

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
async def health() -> HealthResponse:
    return HealthResponse()
