import logging
from elevenlabs import ElevenLabs
from config.settings import settings

logger = logging.getLogger(__name__)

class ElevenLabsClient:
    @classmethod
    def connect(cls) -> "ElevenLabs | None":
        if not settings.elevenlabs_api_key:
            logger.warning("ELEVENLABS_API_KEY not set — ElevenLabs disabled")
            return None
        client = ElevenLabs(api_key=settings.elevenlabs_api_key)
        logger.info("ElevenLabs client connected")
        return client
