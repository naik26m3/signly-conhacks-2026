import asyncio
import io
import logging
import re

logger = logging.getLogger(__name__)

_NOISE_RE = re.compile(r'[\(\[\<][^\)\]\>]{1,60}[\)\]\>]')


class SpeechService:
    def __init__(self, elevenlabs=None, voice_id: str = "21m00Tcm4TlvDq8ikWAM"):
        self._client = elevenlabs  # used for both STT and TTS
        self._voice_id = voice_id

    async def transcribe(self, audio_bytes: bytes, content_type: str = "audio/m4a") -> str:
        if not self._client:
            logger.warning("ElevenLabs not configured — returning empty transcript")
            return ""
        result = await asyncio.to_thread(
            self._client.speech_to_text.convert,
            file=io.BytesIO(audio_bytes),
            model_id="scribe_v1",
            language_code="en",
            tag_audio_events=False,
        )
        raw = result.text if hasattr(result, "text") else str(result)
        text = re.sub(r'\s+', ' ', _NOISE_RE.sub('', raw)).strip()
        logger.info("transcribe: %d bytes → %r (raw: %r)", len(audio_bytes), text[:80], raw[:80])
        return text

    async def synthesize(self, text: str) -> bytes:
        if not self._client:
            raise RuntimeError("ElevenLabs not configured — cannot synthesize speech")
        chunks = await asyncio.to_thread(
            self._client.text_to_speech.convert,
            voice_id=self._voice_id,
            text=text,
            model_id="eleven_multilingual_v2",
        )
        audio = b"".join(chunks) if hasattr(chunks, "__iter__") else chunks
        logger.info("synthesize: %d chars → %d bytes (ElevenLabs)", len(text), len(audio))
        return audio
