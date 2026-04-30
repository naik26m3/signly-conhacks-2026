import asyncio
import json
import logging
import re
from pathlib import Path

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

_FAST_MODEL = "gemini-2.5-flash-lite"

# Files API is only needed for videos > 19MB — most sign clips are well under this
_INLINE_SIZE_LIMIT = 19 * 1024 * 1024

# Gemini's default video sampling is 1 fps, which misses signs faster than ~1s.
# 3 fps captures fast motion modifiers (WHERE shake, teen-number twist) reliably.
_VIDEO_FPS = 3.0

_DEMO_VOCABULARY_PRIOR = (
    "Context — possible demo phrases (use ONLY as a tie-breaker, NOT as a default):\n"
    "The clip might be one of these five demo phrases, but DO NOT guess. First analyse the\n"
    "actual handshapes, locations, and motion you see. Only after identifying the real signs\n"
    "should you check whether they match one of these candidates:\n"
    "\n"
    "  1. HI, WHAT YOUR NAME?       (HI/HELLO greeting + 'what' question)\n"
    "  2. MY NAME K-A-I.  HOW YOU?\n"
    "  3. WHAT YOUR FAVORITE FOOD?\n"
    "  4. I LOVE P-H-O.  WHERE YOU LIVE?\n"
    "  5. ME TOO.  NICE MEET YOU.\n"
    "\n"
    "RULES for using this list:\n"
    "  • DO NOT default to phrase 1 just because it is listed first.\n"
    "  • DO NOT match a phrase unless the handshapes you actually see line up with it.\n"
    "  • If the actual signs don't match any of the 5 phrases, output what you actually see.\n"
    "    Example: if the signer just signs 'I LOVE FOOD' and stops, output that — don't pad\n"
    "    it into 'I LOVE P-H-O. WHERE YOU LIVE?'.\n"
    "  • Confidence 1.0 should be RARE — only when you're certain about every sign. Use\n"
    "    0.7-0.9 if some signs are clear and others are ambiguous.\n"
    "\n"
    "ANTI-TRUNCATION (only when the data supports it):\n"
    "  Each demo clip is intended to contain TWO sentences. If you see signs from BOTH\n"
    "  sentences of a phrase, include both. But if you only see one sentence, output one.\n"
    "  • If you see WHERE + YOU + upward-sliding handshape → output 'WHERE YOU LIVE',\n"
    "    not just 'WHERE'.\n"
    "  • If you see HI (or HELLO) followed by a question gesture → output 'HI, WHAT YOUR NAME',\n"
    "    not just 'HI'. There is only ONE greeting sign — never output 'HI HELLO' together.\n"
    "  • If you see I + LOVE + fingerspelling → output 'I LOVE P-H-O',\n"
    "    not 'I LOVE PIZZA' or anything else.\n"
    "  • If you see fingerspelling of a 3-letter name after 'MY NAME' → it is K-A-I,\n"
    "    NEVER 'K-H-A-I' or 'KHAI'. Kai has exactly 3 letters: K, A, I.\n"
    "\n"
    "ENGLISH OUTPUT RULES (very important):\n"
    "  The 'english' field MUST be GRAMMATICAL English with proper verbs and articles —\n"
    "  NEVER raw gloss-style. Always include 'is/am/are' and articles where natural.\n"
    "  • Gloss 'MY NAME K-A-I' → english 'My name is Kai.'   (NOT 'My name Kai')\n"
    "  • Gloss 'HOW YOU' → english 'How are you?'           (NOT 'How you')\n"
    "  • Gloss 'WHERE YOU LIVE' → english 'Where do you live?'\n"
    "  • Gloss 'WHAT YOUR NAME' → english 'What is your name?'\n"
    "  • Gloss 'WHAT YOUR FAVORITE FOOD' → english 'What is your favorite food?'\n"
    "  • Gloss 'I LOVE P-H-O' → english 'I love Pho.'\n"
    "  • Gloss 'NICE MEET YOU' → english 'Nice to meet you.'\n"
    "  • Gloss 'ME TOO' → english 'Me too.'\n"
    "  When the clip has TWO sentences, the english field should contain BOTH, joined naturally:\n"
    "  • Gloss 'MY NAME K-A-I. HOW YOU?' → english 'My name is Kai. How are you?'\n"
    "  • Gloss 'HI, WHAT YOUR NAME?' → english 'Hi, what is your name?'\n"
    "  • Gloss 'I LOVE P-H-O. WHERE YOU LIVE?' → english 'I love Pho. Where do you live?'\n"
    "\n"
    "Common standalone signs in this conversation: I, ME, YOU, MY, YOUR, NAME, HI, HELLO,\n"
    "HOW, WHAT, WHERE, FAVORITE, FOOD, LOVE, LIVE, NICE, MEET, GOOD, DAY, TOO.\n"
    "Names are exactly 3 letters: KAI (K-A-I), PHO (P-H-O). Never pad with extra letters.\n"
)

_DISAMBIGUATION_RULES = (
    "Critical disambiguation rules:\n"
    "  • Numbers 1-9 are STATIC handshapes (no motion). Numbers 11-19 share the same handshape\n"
    "    as the matching single digit but always include a characteristic motion modifier:\n"
    "      11 = '1' + index-finger flick;   12 = '2' + double finger-flick\n"
    "      13 = '3' + thumb shake;          14 = '4' + four-finger wiggle\n"
    "      15 = '5' + five-finger wiggle;   16 = '6' + small wrist twist (palm rotates outward)\n"
    "      17 = '7' + small wrist twist;    18 = '8' + small wrist twist\n"
    "      19 = '9' + small wrist twist (this is the F-handshape rotating)\n"
    "    If the hand is STILL, it's the single digit. If the hand has small repeated motion or\n"
    "    twist, it's the teen.\n"
    "  • Same handshape at different face locations = different signs:\n"
    "      forehead = FATHER / THINK / KNOW;  chin = MOTHER;  chest = FEEL / PLEASE / SORRY.\n"
    "  • Motion-modified signs to watch for: COME (toward signer) vs GO (away),\n"
    "    HOW (rotating fists) vs WHO (chin tap), HELLO (salute) vs HI (wave).\n"
    "  • CRITICAL — '1' (digit) vs WHERE: same '1' handshape (index finger pointed up).\n"
    "      • '1' = STATIC. Hand stays still.\n"
    "      • WHERE = same handshape but with RAPID SIDE-TO-SIDE SHAKE (3-5 oscillations).\n"
    "        In landmark velocity, dx alternates sign frequently (left/right/left/right).\n"
    "        If you see this wiggle, it is WHERE — NEVER output just '1'.\n"
    "  • LIVE: 'L' or 'A' handshape (both hands or one) sliding UPWARD along the chest/torso.\n"
    "      Wrist velocity dy is consistently NEGATIVE (moving up). The hand path traces from\n"
    "      lower torso/abdomen up toward the chest. Often used after WHERE YOU as 'WHERE YOU LIVE'.\n"
    "  • If you see WHERE followed by YOU followed by an upward-sliding handshape, output\n"
    "    'WHERE YOU LIVE' — don't truncate to just 'WHERE' or 'WHERE YOU'.\n"
    "\nAnti-hallucination rule: it is BETTER to output UNKNOWN than to invent letters or numbers.\n"
    "If a fingerspelled letter is not 100% clear, do NOT include it. If you only see partial motion,\n"
    "say UNKNOWN. Do not pad the gloss with extra letters or numbers if the signer stops or rests.\n"
)

_RECOGNIZE_PROMPT_VIDEO_ONLY = (
    "You are an expert ASL interpreter. Watch this video and identify every ASL sign or fingerspelled word actually performed.\n\n"
    "Pay close attention to handshape, location relative to the face/body, MOVEMENT (or lack of it),\n"
    "speed, and palm orientation.\n\n"
    + _DEMO_VOCABULARY_PRIOR + "\n"
    + _DISAMBIGUATION_RULES +
    "\nRespond with ONLY a single JSON object, no markdown, no array:\n"
    '{"gloss": "GLOSS", "english": "natural English", "confidence": 0.0}\n'
    "- gloss: uppercase ASL gloss (e.g. MY NAME K-A-I, I NEED WATER)\n"
    "- english: natural English translation\n"
    "- confidence: 0.0-1.0 (use ≤0.6 if you are guessing about any letter or number)\n"
    '- If unclear: {"gloss": "UNKNOWN", "english": "Sign not recognised", "confidence": 0.0}'
)

_RECOGNIZE_PROMPT_WITH_LANDMARKS = (
    "You are an expert ASL interpreter. Watch this video and identify every ASL sign or fingerspelled word.\n\n"
    "Per-frame tracking data (every 3rd frame, coordinates normalized 0-1):\n"
    "{landmark_json}\n\n"
    "Each frame entry contains:\n"
    "  face: dict of named facial landmarks, each as [x, y]:\n"
    "    forehead, chin, nose_tip, left_cheek, right_cheek, mouth_left, mouth_right,\n"
    "    left_eyebrow, right_eyebrow.\n"
    "    Use these to determine EXACTLY where each hand is touching or pointing on the face.\n"
    "    Compute distance from a hand fingertip (e.g. right[8] = index tip) to each face landmark —\n"
    "    the smallest distance tells you which face region the sign is anchored to.\n"
    "  right / left: 21 hand landmarks [x, y, z] — index 0 is wrist, 4/8/12/16/20 are fingertips\n"
    "  right_vel / left_vel: [dx, dy] wrist movement since previous frame — positive y = moving down, negative y = moving up.\n"
    "  IMPORTANT: large velocity magnitudes ⇒ the sign has MOTION (likely a teen number, COME/GO, HELLO/HI etc).\n"
    "  Velocity near zero ⇒ STATIC handshape (likely a single digit or stationary sign).\n\n"
    "Use ALL THREE sources: video motion, hand-to-face-landmark distances, and velocity vectors.\n\n"
    + _DEMO_VOCABULARY_PRIOR.replace("{", "{{").replace("}", "}}") + "\n"
    + _DISAMBIGUATION_RULES.replace("{", "{{").replace("}", "}}") +
    "\nRespond with ONLY a single JSON object, no markdown, no array:\n"
    '{{"gloss": "GLOSS", "english": "natural English", "confidence": 0.0}}\n'
    "- gloss: uppercase ASL gloss (e.g. MY NAME K-A-I, I NEED WATER)\n"
    "- english: natural English translation\n"
    "- confidence: 0.0-1.0 (use ≤0.6 if you are guessing about any letter or number)\n"
    '- If unclear: {{"gloss": "UNKNOWN", "english": "Sign not recognised", "confidence": 0.0}}'
)

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

    async def recognize_sign(
        self,
        video_path: str,
        landmark_sequence: list[dict],
        mime_type: str = "video/mp4",
        debug_id: str = "",
    ) -> dict:
        if not self._gemini:
            return {"gloss": "NO_KEY", "english": "Gemini API key not configured", "confidence": 0.0}

        gemini_mime = "video/quicktime" if mime_type == "video/quicktime" else "video/mp4"
        if landmark_sequence:
            landmark_json = json.dumps(landmark_sequence, separators=(",", ":"))
            prompt = _RECOGNIZE_PROMPT_WITH_LANDMARKS.format(landmark_json=landmark_json)
        else:
            prompt = _RECOGNIZE_PROMPT_VIDEO_ONLY

        video_bytes = Path(video_path).read_bytes()
        size_mb = len(video_bytes) / 1024 / 1024
        use_inline = len(video_bytes) < _INLINE_SIZE_LIMIT

        # Cap reasoning latency. thinking_budget=0 disables thinking entirely and works on
        # both Gemini 2.5 (Flash + Pro) and 3.x (which would otherwise want thinking_level).
        # 'thinking_level' is 3.x-only and 400s on 2.5 models.
        # automatic_function_calling.disable=True avoids an internal SDK loop that can cause
        # the call to hang for 60-90s on otherwise short requests.
        gen_config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=0),
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

        # Dump exactly what we're sending to Gemini, so the user can inspect the request.
        if debug_id:
            try:
                debug_dir = Path("/debug/prompts")
                debug_dir.mkdir(parents=True, exist_ok=True)
                header = (
                    f"=== Gemini request — video_id={debug_id} ===\n"
                    f"model: {_FAST_MODEL}\n"
                    f"thinking_level: low\n"
                    f"video_fps_to_gemini: {_VIDEO_FPS}\n"
                    f"video_size_mb: {size_mb:.2f}\n"
                    f"video_mime: {gemini_mime}\n"
                    f"landmark_frames: {len(landmark_sequence)}\n"
                    f"prompt_chars: {len(prompt)}\n\n"
                    f"=== PROMPT (with inlined landmarks) ===\n"
                )
                (debug_dir / f"{debug_id}.txt").write_text(header + prompt, encoding="utf-8")
            except Exception:
                logger.warning("Could not write debug prompt for %s", debug_id, exc_info=True)

        logger.info(
            "recognize_sign: start video=%s size=%.1fMB landmark_frames=%d mode=%s",
            video_path, size_mb, len(landmark_sequence), "inline" if use_inline else "files-api",
        )

        video_metadata = types.VideoMetadata(fps=_VIDEO_FPS)

        try:
            if use_inline:
                # Fast path: embed video bytes directly — no upload, no ACTIVE wait
                video_part = types.Part(
                    inline_data=types.Blob(data=video_bytes, mime_type=gemini_mime),
                    video_metadata=video_metadata,
                )
                response = await asyncio.wait_for(
                    self._gemini.aio.models.generate_content(
                        model=_FAST_MODEL,
                        contents=[video_part, prompt],
                        config=gen_config,
                    ),
                    timeout=30.0,
                )
            else:
                # Large video fallback: use Files API
                uploaded = None
                try:
                    uploaded = await self._gemini.aio.files.upload(
                        file=video_path,
                        config={"mime_type": gemini_mime},
                    )
                    logger.info("recognize_sign: uploaded → %s (state=%s)", uploaded.name, uploaded.state)
                    for _ in range(30):
                        if uploaded.state.name == "ACTIVE":
                            break
                        await asyncio.sleep(1)
                        uploaded = await self._gemini.aio.files.get(name=uploaded.name)
                    else:
                        raise RuntimeError(f"Gemini file {uploaded.name} never became ACTIVE")

                    video_part = types.Part(
                        file_data=types.FileData(file_uri=uploaded.uri, mime_type=gemini_mime),
                        video_metadata=video_metadata,
                    )
                    response = await self._gemini.aio.models.generate_content(
                        model=_FAST_MODEL,
                        contents=[video_part, prompt],
                        config=gen_config,
                    )
                finally:
                    if uploaded:
                        try:
                            await self._gemini.aio.files.delete(name=uploaded.name)
                        except Exception:
                            pass

            raw_text = response.text.strip()
            logger.info("recognize_sign: Gemini raw response: %s", raw_text[:500])

            text = re.sub(r"^```(?:json)?\s*", "", raw_text)
            text = re.sub(r"\s*```$", "", text)

            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                logger.warning("recognize_sign: non-JSON from Gemini: %s", raw_text[:500])
                return {"gloss": "UNKNOWN", "english": "Sign not recognised", "confidence": 0.0}

            result = parsed[0] if isinstance(parsed, list) else parsed

            gloss = str(result.get("gloss", "UNKNOWN"))
            confidence = float(result.get("confidence", 0.0))
            english = str(result.get("english", ""))
            logger.info("recognize_sign: gloss=%s english=%r confidence=%.2f", gloss, english, confidence)

            if confidence < 0.6:
                gloss = "signing..."

            return {"gloss": gloss, "english": english, "confidence": confidence}

        except asyncio.TimeoutError:
            logger.error("recognize_sign: Gemini call timed out after 30s")
            return {"gloss": "TIMEOUT", "english": "Recognition timed out — please retry", "confidence": 0.0}
        except Exception:
            logger.error("recognize_sign: exception during Gemini call", exc_info=True)
            return {"gloss": "UNKNOWN", "english": "Sign not recognised", "confidence": 0.0}

    async def gloss_to_english(self, gloss: str) -> str:
        if not self._gemini:
            return gloss
        response = await self._gemini.aio.models.generate_content(
            model=_FAST_MODEL,
            contents=[_GLOSS_TO_ENGLISH_PROMPT.format(gloss=gloss)],
        )
        return response.text.strip()

    async def english_to_gloss(self, text: str) -> str:
        if not self._gemini:
            return text.upper()
        response = await self._gemini.aio.models.generate_content(
            model=_FAST_MODEL,
            contents=[_ENGLISH_TO_GLOSS_PROMPT.format(text=text)],
        )
        return response.text.strip()
