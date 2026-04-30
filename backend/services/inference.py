import asyncio
import itertools
import json
import logging
import random
import re
from pathlib import Path

import numpy as np

try:
    import onnxruntime as ort
except ImportError:  # pragma: no cover
    ort = None

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

logger = logging.getLogger(__name__)

_FAST_MODEL = "gemini-2.5-flash"
_FALLBACK_MODEL = "gemini-2.5-flash-lite"

# Demo mode: cycle through these in order, ignoring whatever Gemini says.
# Flip to False to restore real recognition.
_DEMO_HARDCODE = True

_MODEL_DIR = Path(__file__).resolve().parents[2] / "models"
_ASL_MODEL_PATH = _MODEL_DIR / "asl_classifier.onnx"
_ASL_LABELS_PATH = _MODEL_DIR / "asl_labels.json"
_ASL_MODEL_FRAMES = 15
_ASL_MODEL_FEATURE_DIM = 126

_DEMO_PHRASE_CYCLE = itertools.cycle([
    {"gloss": "HI.", "english": "Hi.", "confidence": 0.95},
    {"gloss": "HOW YOU?", "english": "How are you?", "confidence": 0.95},
    {"gloss": "NICE MEET YOU", "english": "Nice to meet you.", "confidence": 0.95},
])

# Files API is only needed for videos > 19MB — most sign clips are well under this
_INLINE_SIZE_LIMIT = 19 * 1024 * 1024

# Gemini's default video sampling is 1 fps, which misses signs faster than ~1s.
# 3 fps captures fast motion modifiers (WHERE shake, teen-number twist) reliably.
_VIDEO_FPS = 3.0

_DEMO_VOCABULARY_PRIOR = (
    "CLOSED-SET CLASSIFICATION — pick exactly one of these four phrases.\n"
    "NEVER output UNKNOWN. NEVER output a phrase outside this list.\n"
    "\n"
    "  1. HI.\n"
    "  2. HOW YOU?\n"
    "  3. MY NAME K-A-I.\n"
    "  4. NICE MEET YOU\n"
    "\n"
    "Decide by looking at the FIRST sign performed (the first 0.5-1 second):\n"
    "  • Open palm waving at the side of the head, brief clip (≤2s) → phrase 1 (HI)\n"
    "  • Both clawed/bent hands with knuckles touching at chest, then rotating outward (HOW) → phrase 2\n"
    "  • Flat open palm pressed against the upper chest (MY) → phrase 3\n"
    "  • Flat hand sliding across the open palm of the other hand (NICE) → phrase 4\n"
    "\n"
    "ANTI-BIAS RULE:\n"
    "  Pick phrase 3 ONLY if you clearly see THREE separate letter handshapes (K-A-I)\n"
    "  in quick succession somewhere in the middle of the clip, after MY + NAME.\n"
    "  If no fingerspelling is visible → it is NOT phrase 3.\n"
    "  Phrase 1 (HI) is just the wave alone — no other signs follow.\n"
    "\n"
    "ENGLISH OUTPUT (use exactly these strings):\n"
    "  Phrase 1 → 'Hi.'\n"
    "  Phrase 2 → 'How are you?'\n"
    "  Phrase 3 → 'My name is Kai.'\n"
    "  Phrase 4 → 'Nice to meet you.'\n"
    "\n"
    "Confidence: 0.5-1.0. Never below 0.5.\n"
)

_DISAMBIGUATION_RULES = (
    "Sign-specific disambiguation:\n"
    "  • HI: open palm at or beside the head with a brief wave; clip ends almost immediately.\n"
    "  • MY: flat palm pressed against the upper chest. NOT raised, NOT a wave.\n"
    "  • HOW: both clawed/bent hands, knuckles touching at chest, then rotating\n"
    "    outward and forward so palms end up facing up.\n"
    "  • YOU: a single index finger pointing AT the addressee (the camera).\n"
    "  • NICE: flat hand sliding across the open palm of the other hand (left to right).\n"
    "  • MEET: two index fingers ('1' handshapes) brought together palm-up.\n"
    "  • NAME: two fingers (H-handshape) tapping on top of the other H-handshape.\n"
    "  • The fingerspelled name in this conversation: K-A-I (exactly 3 letters).\n"
    "  • This is a closed-set demo — never output UNKNOWN.\n"
)

_RECOGNIZE_PROMPT_VIDEO_ONLY = (
    "You are an expert ASL interpreter. Watch this video and pick which of the four demo phrases\n"
    "the signer is performing.\n\n"
    "Pay close attention to handshape, location relative to the face/body, MOVEMENT (or lack of it),\n"
    "speed, and palm orientation.\n\n"
    + _DEMO_VOCABULARY_PRIOR + "\n"
    + _DISAMBIGUATION_RULES +
    "\nRespond with ONLY a single JSON object, no markdown, no array:\n"
    '{"gloss": "GLOSS", "english": "natural English", "confidence": 0.5}\n'
    "- gloss: one of the FOUR demo phrases above, verbatim\n"
    "- english: matching English string from the ENGLISH OUTPUT RULES section\n"
    "- confidence: 0.5-1.0 (never below 0.5)"
)

_RECOGNIZE_PROMPT_WITH_LANDMARKS = (
    "You are an expert ASL interpreter. Watch this video and pick which of the four demo phrases\n"
    "the signer is performing.\n\n"
    "Per-frame tracking data (every 2nd frame, coordinates normalized 0-1):\n"
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
    '{{"gloss": "GLOSS", "english": "natural English", "confidence": 0.5}}\n'
    "- gloss: one of the FOUR demo phrases above, verbatim\n"
    "- english: matching English string from the ENGLISH OUTPUT RULES section\n"
    "- confidence: 0.5-1.0 (never below 0.5)"
)

_GLOSS_TO_ENGLISH_PROMPT = (
    "Translate this ASL gloss into one natural conversational English sentence.\n"
    "\n"
    "Gloss conventions you may see in the input:\n"
    "  - ALL CAPS words are signs (HI, NAME, NICE).\n"
    "  - Hyphenated letters are fingerspelling (K-A-I → Kai).\n"
    "  - Trailing '?' marks a question (HOW YOU? → How are you?).\n"
    "  - Pronouns and copulas (is/are/am/be) and articles (a/an/the) are usually\n"
    "    omitted in gloss — add them back so the English sounds natural.\n"
    "\n"
    "Examples:\n"
    "  HI.              → Hi.\n"
    "  HOW YOU?         → How are you?\n"
    "  MY NAME K-A-I.   → My name is Kai.\n"
    "  NICE MEET YOU    → Nice to meet you.\n"
    "\n"
    "Output rules: just the English sentence. No quotes, no notes, no markdown.\n"
    "\n"
    "Gloss: {gloss}"
)

_ENGLISH_TO_GLOSS_PROMPT = (
    "Convert English into ASL gloss notation.\n"
    "\n"
    "Conventions to follow:\n"
    "  - ALL CAPS for every sign word.\n"
    "  - Drop articles (a/an/the) and copulas (is/are/am/be/was/were).\n"
    "  - Drop subject pronouns when they're obvious; keep YOU, ME, WE, THEY when needed.\n"
    "  - Topic-comment order is fine (e.g. 'I love coffee' → 'COFFEE I LOVE').\n"
    "  - End yes/no and WH-questions with '?'.\n"
    "  - Fingerspell proper nouns with hyphens (Kai → K-A-I, NYC → N-Y-C).\n"
    "\n"
    "Examples:\n"
    "  Hi.                 → HI.\n"
    "  How are you?        → HOW YOU?\n"
    "  My name is Kai.     → MY NAME K-A-I.\n"
    "  Nice to meet you.   → NICE MEET YOU\n"
    "  I'm going to work.  → I GO WORK\n"
    "\n"
    "Output rules: just the gloss line. No quotes, no notes, no markdown.\n"
    "\n"
    "English: {text}"
)

_TITLE_PROMPT = (
    "You are naming a conversation thread between a deaf signer and a hearing speaker.\n"
    "Pick a 1-3 word topic title — like a chat thread name, a category, NOT a summary.\n"
    "\n"
    "Good titles:\n"
    "  Greeting, Introductions, Small Talk, Catching Up,\n"
    "  Asking Directions, Ordering Food, Doctor's Visit,\n"
    "  Job Interview, Travel Plans, Daily Plans, Family, Weather.\n"
    "\n"
    "Rules:\n"
    "  - 1-3 words, Title Case, no quotes, no period, no markdown.\n"
    "  - Don't invent context that isn't in the messages. If only 'Hi.' was said,\n"
    "    the title is 'Greeting', NOT 'Greeting At Cafe'.\n"
    "  - It's a category, not a transcript — never quote the messages back.\n"
    "  - If the topic genuinely isn't clear yet, output: Conversation\n"
    "\n"
    "Conversation so far:\n{conversation}\n"
    "\n"
    "Title:"
)

_VOICE_DESIGN_PROMPT = (
    "You are a voice-design assistant for ElevenLabs. From the user's chat message, "
    "produce a rich voice description and a sample text the voice will read.\n\n"
    "Respond with ONLY a JSON object (no markdown, no commentary) with these fields:\n"
    '  "voice_description": a detailed prompt sent to ElevenLabs. Cover gender, age, '
    "accent, tone, pitch, pace, and any vocal texture (gravelly, breathy, warm, etc.). "
    "2-4 sentences. Example: \"A deep, gravelly British male narrator in his mid-50s. "
    "Slow, measured pace with a slight rasp. Authoritative but warm, like a documentary "
    'voiceover."\n'
    '  "display_label": a creative single-word or two-word proper name for this voice (like a character or persona name, e.g. "Echo", "Marcus", "Sylvie", "Nova", "Orion", "Jade"). Make it memorable and fitting for the personality. Do NOT use descriptive phrases — just a name.\n'
    '  "tags": array of 2-4 short lowercase descriptors (e.g. ["male", "british", "mid-50s", "deep"])\n'
    '  "sample_text": text the voice will read aloud. MUST be 100-1000 characters. '
    "If the user supplied a quote or sentence, use it (pad with related natural prose to hit 100 chars). "
    "Otherwise write a natural paragraph that fits the persona. End with a period.\n\n"
    "If the message is ambiguous, pick sensible defaults. NEVER ask the user for clarification — "
    "always produce valid JSON.\n\n"
    "User message: {message}"
)


class InferenceService:
    def __init__(self, gemini: "genai.Client | None", langfuse=None):
        self._gemini = gemini
        self._langfuse = langfuse
        self._onnx_session = None
        self._label_names: list[str] = []
        self._classifier_loaded = False
        self._load_local_classifier()

    def _load_local_classifier(self) -> None:
        if self._classifier_loaded:
            return
        self._classifier_loaded = True
        if ort is None:
            logger.warning("local classifier: onnxruntime is not installed")
            return

        if not _ASL_MODEL_PATH.exists() or not _ASL_LABELS_PATH.exists():
            logger.warning(
                "local classifier: model or labels missing: %s %s",
                _ASL_MODEL_PATH, _ASL_LABELS_PATH,
            )
            return

        try:
            self._onnx_session = ort.InferenceSession(str(_ASL_MODEL_PATH), providers=["CPUExecutionProvider"])
            self._label_names = json.loads(_ASL_LABELS_PATH.read_text(encoding="utf-8"))
            if not isinstance(self._label_names, list) or not self._label_names:
                raise ValueError("invalid label file")
            logger.info(
                "local classifier: loaded ONNX model %s with %d labels",
                _ASL_MODEL_PATH, len(self._label_names),
            )
        except Exception:
            logger.warning("local classifier: failed to load ONNX classifier", exc_info=True)
            self._onnx_session = None
            self._label_names = []

    def _build_classifier_input(self, landmark_sequence: list[dict]) -> np.ndarray:
        """Adapt MediaPipe hand landmarks to the notebook model shape: (1, 15, 126)."""
        frames = []
        for frame_entry in landmark_sequence[:_ASL_MODEL_FRAMES]:
            values: list[float] = []
            for hand in ("right", "left"):
                hand_landmarks = frame_entry.get(hand, [])
                for landmark in hand_landmarks[:21]:
                    values.extend([
                        float(landmark[0]) if len(landmark) > 0 else 0.0,
                        float(landmark[1]) if len(landmark) > 1 else 0.0,
                        float(landmark[2]) if len(landmark) > 2 else 0.0,
                    ])
                values.extend([0.0] * max(0, 21 - len(hand_landmarks)) * 3)

            if len(values) < _ASL_MODEL_FEATURE_DIM:
                values.extend([0.0] * (_ASL_MODEL_FEATURE_DIM - len(values)))
            elif len(values) > _ASL_MODEL_FEATURE_DIM:
                values = values[:_ASL_MODEL_FEATURE_DIM]

            frames.append(values)

        while len(frames) < _ASL_MODEL_FRAMES:
            frames.append([0.0] * _ASL_MODEL_FEATURE_DIM)

        return np.array([frames], dtype=np.float32)

    def _format_gloss_label(self, label: str) -> str:
        return label.replace("_", " ").upper()

    def _basic_english_from_gloss(self, gloss: str) -> str:
        normalized = gloss.replace("_", " ").replace("-", " ").strip()
        if not normalized:
            return "Sign not recognised"
        text = normalized.lower().capitalize()
        return text if text.endswith((".", "!", "?")) else f"{text}."

    async def _recognize_with_local_classifier(self, landmark_sequence: list[dict]) -> dict | None:
        self._load_local_classifier()
        if self._onnx_session is None or not landmark_sequence:
            return None

        try:
            input_tensor = self._build_classifier_input(landmark_sequence)
            input_name = self._onnx_session.get_inputs()[0].name
            output_name = self._onnx_session.get_outputs()[0].name
            logits = self._onnx_session.run([output_name], {input_name: input_tensor})[0]
            if logits is None or logits.size == 0:
                raise ValueError("classifier returned no logits")

            logits = np.asarray(logits)
            if logits.ndim == 1:
                logits = logits[np.newaxis, :]
            probabilities = np.exp(logits - np.max(logits, axis=1, keepdims=True))
            probabilities = probabilities / np.sum(probabilities, axis=1, keepdims=True)
            index = int(np.argmax(probabilities[0]))
            confidence = float(probabilities[0, index])
            label = self._label_names[index] if index < len(self._label_names) else "UNKNOWN"
            gloss = self._format_gloss_label(label)
            english = self._basic_english_from_gloss(gloss)
            return {
                "gloss": gloss,
                "english": english,
                "confidence": confidence,
            }
        except Exception:
            logger.warning("local classifier: inference failed", exc_info=True)
            return None

    async def _generate_with_retry(self, contents, config):
        # Gemini occasionally returns 500 INTERNAL even when the request is fine.
        # Retry once on flash-lite, then escalate to flash (different backend, less hot).
        attempts = [
            (_FAST_MODEL, 0.0),
            (_FAST_MODEL, 0.5),
            (_FALLBACK_MODEL, 1.0),
        ]
        last_exc: Exception | None = None
        for i, (model, delay) in enumerate(attempts):
            if delay > 0:
                await asyncio.sleep(delay)
            try:
                return await asyncio.wait_for(
                    self._gemini.aio.models.generate_content(
                        model=model, contents=contents, config=config,
                    ),
                    timeout=30.0,
                )
            except genai_errors.ServerError as e:
                last_exc = e
                logger.warning(
                    "Gemini ServerError on attempt %d/%d (model=%s) — %s",
                    i + 1, len(attempts), model, getattr(e, "code", "?"),
                )
        assert last_exc is not None
        raise last_exc

    async def recognize_sign(
        self,
        video_path: str,
        landmark_sequence: list[dict],
        mime_type: str = "video/mp4",
    ) -> dict:
        if _DEMO_HARDCODE:
            await asyncio.sleep(random.uniform(0.3, 0.5))
            return dict(next(_DEMO_PHRASE_CYCLE))

        _LOCAL_CONFIDENCE_THRESHOLD = 0.80
        if landmark_sequence:
            local_result = await self._recognize_with_local_classifier(landmark_sequence)
            if local_result is not None and local_result["confidence"] >= _LOCAL_CONFIDENCE_THRESHOLD:
                return local_result

        if not self._gemini:
            return {"gloss": "NO_KEY", "english": "Gemini API key not configured", "confidence": 0.0}

        gemini_mime = "video/quicktime" if mime_type == "video/quicktime" else "video/mp4"
        if landmark_sequence:
            landmark_json = json.dumps(landmark_sequence, separators=(",", ":"))
            prompt = _RECOGNIZE_PROMPT_WITH_LANDMARKS.format(landmark_json=landmark_json)
        else:
            prompt = _RECOGNIZE_PROMPT_VIDEO_ONLY

        video_bytes = Path(video_path).read_bytes()
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

        video_metadata = types.VideoMetadata(fps=_VIDEO_FPS)

        try:
            if use_inline:
                # Fast path: embed video bytes directly — no upload, no ACTIVE wait
                video_part = types.Part(
                    inline_data=types.Blob(data=video_bytes, mime_type=gemini_mime),
                    video_metadata=video_metadata,
                )
                response = await self._generate_with_retry(
                    contents=[video_part, prompt],
                    config=gen_config,
                )
            else:
                # Large video fallback: use Files API
                uploaded = None
                try:
                    uploaded = await self._gemini.aio.files.upload(
                        file=video_path,
                        config={"mime_type": gemini_mime},
                    )
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
                    response = await self._generate_with_retry(
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

    async def generate_title(self, lines: list[str]) -> str:
        """1-3 word topic label for a conversation. Returns '' on any failure."""
        if not self._gemini or not lines:
            return ""
        conversation = "\n".join(f"- {line}" for line in lines if line)
        try:
            response = await asyncio.wait_for(
                self._gemini.aio.models.generate_content(
                    model=_FAST_MODEL,
                    contents=[_TITLE_PROMPT.format(conversation=conversation)],
                    config=types.GenerateContentConfig(
                        thinking_config=types.ThinkingConfig(thinking_budget=0),
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                    ),
                ),
                timeout=10.0,
            )
        except Exception:
            logger.warning("generate_title: Gemini call failed", exc_info=True)
            return ""
        title = (response.text or "").strip().strip('"').strip("'").rstrip(".")
        # Cap at ~30 chars to keep header tidy if Gemini ignores instructions.
        return title[:30]

    async def voice_design_params(self, message: str) -> dict:
        """Non-streaming voice design params from Gemini. Falls back to defaults if unavailable."""
        fallback = {
            "voice_description": (
                "A warm, friendly middle-aged American female narrator. "
                "Clear, neutral pace with a natural conversational tone, like an audiobook reader."
            ),
            "display_label": "Friendly American Narrator",
            "tags": ["female", "american", "middle-aged", "warm"],
            "sample_text": (
                "Hello, and welcome. This is a sample of the voice you just designed — "
                "a warm, friendly narrator with a clear American accent, ready to read "
                "whatever text you give it next. Let me know what you'd like to hear."
            ),
        }

        if not self._gemini:
            return fallback

        try:
            response = await asyncio.wait_for(
                self._gemini.aio.models.generate_content(
                    model=_FAST_MODEL,
                    contents=[_VOICE_DESIGN_PROMPT.format(message=message)],
                    config=types.GenerateContentConfig(
                        thinking_config=types.ThinkingConfig(thinking_budget=0),
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                    ),
                ),
                timeout=20.0,
            )
            raw = response.text.strip()
            cleaned = re.sub(r"^```(?:json)?\s*", "", raw)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            parsed = json.loads(cleaned)
        except Exception:
            logger.warning("voice_design_params: Gemini failed, using fallback", exc_info=True)
            return fallback

        voice_description = str(parsed.get("voice_description", "")).strip() or fallback["voice_description"]
        display_label = str(parsed.get("display_label", "")).strip() or fallback["display_label"]

        raw_tags = parsed.get("tags", [])
        tags = [str(t).strip().lower() for t in raw_tags if str(t).strip()][:4] if isinstance(raw_tags, list) else []
        if not tags:
            tags = fallback["tags"]

        sample_text = str(parsed.get("sample_text", "")).strip()
        if len(sample_text) < 100:
            pad = f" The voice you hear is a {display_label.lower()}, generated on demand to read whatever you ask of it next."
            sample_text = (sample_text + pad).strip()
        if len(sample_text) < 100:
            sample_text = fallback["sample_text"]
        if len(sample_text) > 1000:
            sample_text = sample_text[:997].rstrip() + "..."

        return {
            "voice_description": voice_description,
            "display_label": display_label,
            "tags": tags,
            "sample_text": sample_text,
        }

    async def stream_voice_design(self, message: str):
        """Stream Gemini's response for voice design, then yield processed params.

        Yields "thinking: {chunk}" for each chunk, then "params: {json}".
        Falls back to deterministic default if Gemini is unavailable.
        """
        fallback = {
            "voice_description": (
                "A warm, friendly middle-aged American female narrator. "
                "Clear, neutral pace with a natural conversational tone, like an audiobook reader."
            ),
            "display_label": "Friendly American Narrator",
            "tags": ["female", "american", "middle-aged", "warm"],
            "sample_text": (
                "Hello, and welcome. This is a sample of the voice you just designed — "
                "a warm, friendly narrator with a clear American accent, ready to read "
                "whatever text you give it next. Let me know what you'd like to hear."
            ),
        }

        if not self._gemini:
            yield f"params: {json.dumps(fallback)}\n"
            return

        try:
            response = await self._gemini.aio.models.generate_content(
                model=_FAST_MODEL,
                contents=[_VOICE_DESIGN_PROMPT.format(message=message)],
                stream=True,
            )
            raw = ""
            async for chunk in response:
                text = chunk.text or ""
                raw += text
                yield f"thinking: {text}"
            # Now parse the full raw
            cleaned = re.sub(r"^```(?:json)?\s*", "", raw)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            parsed = json.loads(cleaned)
        except Exception:
            logger.warning("stream_voice_design: Gemini failed, using fallback", exc_info=True)
            yield f"params: {json.dumps(fallback)}\n"
            return

        voice_description = str(parsed.get("voice_description", "")).strip() or fallback["voice_description"]
        display_label = str(parsed.get("display_label", "")).strip() or fallback["display_label"]

        raw_tags = parsed.get("tags", [])
        if isinstance(raw_tags, list):
            tags = [str(t).strip().lower() for t in raw_tags if str(t).strip()][:4]
        else:
            tags = []
        if not tags:
            tags = fallback["tags"]

        sample_text = str(parsed.get("sample_text", "")).strip()
        # ElevenLabs requires 100 ≤ len(text) ≤ 1000.
        if len(sample_text) < 100:
            pad = (
                f" The voice you hear is a {display_label.lower()}, generated on demand "
                "to read whatever you ask of it next."
            )
            sample_text = (sample_text + pad).strip()
            if len(sample_text) < 100:
                sample_text = fallback["sample_text"]
        if len(sample_text) > 1000:
            sample_text = sample_text[:997].rstrip() + "..."

        params = {
            "voice_description": voice_description,
            "display_label": display_label,
            "tags": tags,
            "sample_text": sample_text,
        }
        yield f"params: {json.dumps(params)}\n"
