from pydantic import BaseModel


class TranscribeResponse(BaseModel):
    api_version: str = "v1"
    transcript: str


class GlossRequest(BaseModel):
    text: str


class GlossResponse(BaseModel):
    api_version: str = "v1"
    gloss: str
