from pydantic import BaseModel


class QueuedResponse(BaseModel):
    api_version: str = "v1"
    video_id: str
    status: str = "processing"


class SignResultResponse(BaseModel):
    api_version: str = "v1"
    video_id: str
    status: str
    gloss: str | None = None
    english: str | None = None
    confidence: float | None = None
    landmarks_found: bool | None = None
    audio_url: str | None = None
    detail: str | None = None


class RecognizeResponse(BaseModel):
    api_version: str = "v1"
    video_id: str
    gloss: str
    english: str
    confidence: float
    landmarks_found: bool


class CorrectionRequest(BaseModel):
    video_id: str
    correct_gloss: str
    notes: str = ""


class CorrectionResponse(BaseModel):
    api_version: str = "v1"
    id: str
    saved: bool = True


class CorrectionsListResponse(BaseModel):
    api_version: str = "v1"
    total: int
    recent: list[dict]
