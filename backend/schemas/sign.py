from pydantic import BaseModel

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
