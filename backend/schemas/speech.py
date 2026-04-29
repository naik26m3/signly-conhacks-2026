from pydantic import BaseModel

class TranscribeResponse(BaseModel):
    api_version: str = "v1"
    transcript: str
    gloss: str
