from pydantic import BaseModel


class VoiceDesignRequest(BaseModel):
    message: str


class VoiceDesignParams(BaseModel):
    voice_description: str
    display_label: str
    tags: list[str]


class VoiceDesignResponse(BaseModel):
    api_version: str = "v1"
    params: VoiceDesignParams
    sample_text: str
    audio_base64: str
    audio_mime: str = "audio/mpeg"


class VoiceSpeakRequest(BaseModel):
    voice_description: str
    text: str


class VoiceSpeakResponse(BaseModel):
    api_version: str = "v1"
    audio_base64: str
    audio_mime: str = "audio/mpeg"
