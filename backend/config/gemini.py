import logging
from google import genai
from config.settings import settings

logger = logging.getLogger(__name__)

class GeminiClient:
    @classmethod
    def connect(cls) -> "genai.Client | None":
        if not settings.gemini_api_key:
            logger.warning("GEMINI_API_KEY not set — Gemini disabled")
            return None
        client = genai.Client(api_key=settings.gemini_api_key)
        logger.info("Gemini client connected")
        return client
