from pydantic import BaseModel


class UploadVideoResponse(BaseModel):
    api_version: str = "v1"
    video_id: str
    status: str = "ready"


class UploadTextResponse(BaseModel):
    api_version: str = "v1"
    message: str
