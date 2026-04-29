import base64
import json
import logging
import re

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

_RECOGNIZE_PROMPT = """\
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

_GLOSS_TO_ENGLISH_PROMPT = (
    "Translate this ASL gloss into a natural English sentence. "
    "Respond with only the English sentence, nothing else. Gloss: {gloss}"
)

_ENGLISH_TO_GLOSS_PROMPT = (
    "Convert this English text into ASL gloss notation (uppercase words, no articles). "
    "Respond with only the gloss, nothing else. English: {text}"
)


class InferenceService:
    def __init__(self, gemini: "genai.Client | None", langfuse=None):
        self._gemini = gemini
        self._langfuse = langfuse

    async def recognize_sign(self, frame_b64: str) -> dict:
        if not self._gemini:
            return {"gloss": "NO_KEY", "english": "Gemini API key not configured", "confidence": 0.0}
        image_bytes = base64.b64decode(frame_b64)
        logger.info("recognize_sign: sending frame (%d bytes) to Gemini", len(image_bytes))

        trace = self._langfuse.trace(name="recognize_sign") if self._langfuse else None
        generation = trace.generation(
            name="gemini-recognize",
            model="gemini-2.0-flash",
            input={"frame_bytes": len(image_bytes)},
        ) if trace else None

        response = await self._gemini.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                _RECOGNIZE_PROMPT,
            ],
        )
        text = response.text.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("recognize_sign: non-JSON from Gemini: %s", text[:200])
            if generation:
                generation.end(output={"error": "non-json"})
            return {"gloss": "UNKNOWN", "english": "Could not parse Gemini response", "confidence": 0.0}

        gloss = str(result.get("gloss", "UNKNOWN"))
        confidence = float(result.get("confidence", 0.0))
        english = str(result.get("english", ""))
        if confidence < 0.6:
            gloss = "signing..."
        if generation:
            generation.end(output={"gloss": gloss, "confidence": confidence})
        logger.info("recognize_sign: gloss=%s confidence=%.2f", gloss, confidence)
        return {"gloss": gloss, "english": english, "confidence": confidence}

    async def gloss_to_english(self, gloss: str) -> str:
        if not self._gemini:
            return gloss
        response = await self._gemini.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents=[_GLOSS_TO_ENGLISH_PROMPT.format(gloss=gloss)],
        )
        return response.text.strip()

    async def english_to_gloss(self, text: str) -> str:
        if not self._gemini:
            return text.upper()
        response = await self._gemini.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents=[_ENGLISH_TO_GLOSS_PROMPT.format(text=text)],
        )
        return response.text.strip()
