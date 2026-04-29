import asyncio
import io
import logging

logger = logging.getLogger(__name__)


class SpeechService:
    _VOICE_ID = "JBFqnCBsd6RMkjVDRTpX"  # ElevenLabs "George" voice

    def __init__(self, elevenlabs=None):
        self._client = elevenlabs  # ElevenLabs | None — passed from config

    async def transcribe(self, audio_bytes: bytes, content_type: str = "audio/m4a") -> str:
        if not self._client:
            logger.warning("ElevenLabs not configured — returning empty transcript")
            return ""
        result = await asyncio.to_thread(
            self._client.speech_to_text.convert,
            audio=io.BytesIO(audio_bytes),
            model_id="scribe_v1",
        )
        text = result.text if hasattr(result, "text") else str(result)
        logger.info("transcribe: %d bytes → %r", len(audio_bytes), text[:80])
        return text

    async def synthesize(self, text: str) -> bytes:
        if not self._client:
            logger.warning("ElevenLabs not configured — returning empty audio")
            return b""
        chunks = await asyncio.to_thread(
            self._client.text_to_speech.convert,
            voice_id=self._VOICE_ID,
            text=text,
            model_id="eleven_multilingual_v2",
        )
        audio = b"".join(chunks) if hasattr(chunks, "__iter__") else chunks
        logger.info("synthesize: %d chars → %d bytes", len(text), len(audio))
        return audio
