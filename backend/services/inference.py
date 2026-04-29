import json
import logging
import re

from google import genai
from google.genai import types
import base64

from config.settings import settings

logger = logging.getLogger(__name__)

_PROMPT = """\
Look at this image of a hand and identify the ASL (American Sign Language) sign being shown.
Respond with ONLY valid JSON in this exact format, no markdown, no extra text:
{
  "gloss": "SIGN_NAME",
  "english": "English meaning",
  "confidence": 0.85
}

Rules:
- gloss: the ASL sign in uppercase (e.g. "HELLO", "THANK_YOU", "I_LOVE_YOU")
- english: natural English translation
- confidence: your confidence from 0.0 to 1.0
- If no clear hand sign is visible: {"gloss": "NO_SIGN", "english": "No sign detected", "confidence": 0.0}
"""

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


async def recognize_sign(frame_b64: str) -> dict:
    if not settings.gemini_api_key:
        logger.warning("GEMINI_API_KEY not set — returning stub response")
        return {"gloss": "NO_KEY", "english": "Gemini API key not configured", "confidence": 0.0}

    client = _get_client()
    image_bytes = base64.b64decode(frame_b64)

    response = await client.aio.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
            _PROMPT,
        ],
    )

    text = response.text.strip()
    # Strip markdown code fences if Gemini wraps the response
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Gemini returned non-JSON: %s", text[:300])
        return {"gloss": "UNKNOWN", "english": "Could not parse Gemini response", "confidence": 0.0}

    gloss = str(result.get("gloss", "UNKNOWN"))
    confidence = float(result.get("confidence", 0.0))
    english = str(result.get("english", ""))

    if confidence < 0.6:
        gloss = "signing..."

    logger.info("Gemini result: gloss=%s english=%s confidence=%.2f", gloss, english, confidence)
    return {"gloss": gloss, "english": english, "confidence": confidence}
