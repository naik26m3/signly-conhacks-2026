from pydantic import BaseModel


class HealthResponse(BaseModel):
    api_version: str = "v1"
    status: str = "ok"
