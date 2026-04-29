import json
import logging
import re

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

_RECOGNIZE_PROMPT_TEMPLATE = """\
You are an ASL sign language interpreter.

You are given:
1. A short video of a person performing an ASL sign
2. Hand landmark coordinates sampled every 3 frames (21 points per hand, normalized x/y/z)

Use both the visual motion in the video AND the landmark trajectory to identify the sign.

Landmark data:
{landmark_json}

Respond with ONLY valid JSON, no markdown:
{{"gloss": "SIGN_NAME", "english": "English meaning", "confidence": 0.85}}

Rules:
- gloss: the ASL sign in uppercase (e.g. "HELLO", "THANK_YOU")
- english: natural English translation
- confidence: 0.0 to 1.0
- If you cannot identify a clear sign: {{"gloss": "UNKNOWN", "english": "Sign not recognised", "confidence": 0.0}}
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

    async def recognize_sign(self, video_path: str, landmark_sequence: list[dict]) -> dict:
        if not self._gemini:
            return {"gloss": "NO_KEY", "english": "Gemini API key not configured", "confidence": 0.0}

        landmark_json = json.dumps(landmark_sequence, separators=(",", ":"))
        prompt = _RECOGNIZE_PROMPT_TEMPLATE.format(landmark_json=landmark_json)

        trace = self._langfuse.trace(name="recognize_sign") if self._langfuse else None
        generation = (
            trace.generation(
                name="gemini-recognize",
                model="gemini-2.5-flash",
                input={"video_path": video_path, "landmark_frames": len(landmark_sequence)},
            )
            if trace
            else None
        )

        uploaded = None
        try:
            uploaded = await self._gemini.aio.files.upload(
                path=video_path,
                config={"mime_type": "video/mp4"},
            )
            logger.info("recognize_sign: uploaded %s → %s", video_path, uploaded.name)

            response = await self._gemini.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part.from_uri(file_uri=uploaded.uri, mime_type="video/mp4"),
                    prompt,
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
                return {"gloss": "UNKNOWN", "english": "Sign not recognised", "confidence": 0.0}

            gloss = str(result.get("gloss", "UNKNOWN"))
            confidence = float(result.get("confidence", 0.0))
            english = str(result.get("english", ""))
            if confidence < 0.6:
                gloss = "signing..."
            if generation:
                generation.end(output={"gloss": gloss, "confidence": confidence})
            logger.info("recognize_sign: gloss=%s confidence=%.2f", gloss, confidence)
            return {"gloss": gloss, "english": english, "confidence": confidence}

        except Exception:
            if generation:
                generation.end(output={"error": "exception"})
            logger.error("recognize_sign: exception during Gemini call", exc_info=True)
            return {"gloss": "UNKNOWN", "english": "Sign not recognised", "confidence": 0.0}

        finally:
            if uploaded:
                try:
                    await self._gemini.aio.files.delete(name=uploaded.name)
                    logger.info("recognize_sign: deleted Gemini file %s", uploaded.name)
                except Exception:
                    logger.warning("recognize_sign: failed to delete %s", uploaded.name, exc_info=True)

    async def gloss_to_english(self, gloss: str) -> str:
        if not self._gemini:
            return gloss
        response = await self._gemini.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=[_GLOSS_TO_ENGLISH_PROMPT.format(gloss=gloss)],
        )
        return response.text.strip()

    async def english_to_gloss(self, text: str) -> str:
        if not self._gemini:
            return text.upper()
        response = await self._gemini.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=[_ENGLISH_TO_GLOSS_PROMPT.format(text=text)],
        )
        return response.text.strip()
