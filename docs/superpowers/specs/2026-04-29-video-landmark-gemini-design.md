# Video + Landmark Gemini Recognition Design

**Date:** 2026-04-29
**Status:** Approved

---

## Problem

The current sign recognition pipeline extracts a single still frame from the uploaded video and sends it to Gemini as a JPEG. This loses all motion information — many ASL signs can only be distinguished by movement, not by a static hand pose. Recognition accuracy suffers as a result.

---

## Solution

Send the full short video to Gemini via the Files API alongside a structured landmark motion sequence extracted by MediaPipe in VIDEO mode. Gemini uses both the visual motion and the precise spatial trajectory to identify the sign.

---

## Communication Direction Affected

**Deaf → Hearing only.** This changes the sign recognition worker pipeline. The hearing → deaf speech transcription flow is untouched.

---

## Key Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| MediaPipe running mode | VIDEO | Tracks landmarks across frames with temporal continuity — designed for video, not per-frame IMAGE mode |
| Video delivery to Gemini | Files API | Handles 30s clips safely; inline bytes has a ~20MB limit |
| Landmark sample rate | Every 3rd frame | Balances accuracy vs payload size (~300 data points max for 30s at 30fps) |
| No-hand fallback | Reject immediately | If MediaPipe can't find hands, video quality is too poor for Gemini to help; save the API call |
| Client video format | H.264 480p max 30s | Forced via `expo-camera` codec option; prevents Apple HEVC weirdness |
| Gemini temp file | Deleted after response | User video data does not linger on Google's servers |
| Frontend / API contract | Unchanged | Same endpoints, same response shape — zero frontend changes |

---

## Architecture

### Pipeline (Worker)

```
Client records video (H.264, 480p, max 30s)
  → POST /api/v1/sign/recognize (unchanged)
  → stored in SeaweedFS (unchanged)

Worker:
  1. Download video from SeaweedFS
  2. Write to temp file
  3. HandTracker.process_video(tmp_path) [VIDEO mode]
       → landmark_sequence: list[dict]  (sampled every 3rd frame)
       → landmarks_found: bool
  4. if not landmarks_found:
       delete tmp file
       write Redis: { status: "done", gloss: "NO_HAND",
                      english: "No hand detected — try again", confidence: 0.0 }
       return  ← no Gemini call, no TTS, no DB insert
  5. inference.recognize_sign(tmp_path, landmark_sequence)
       → upload tmp to Gemini Files API → file_uri
       → generate_content(video=file_uri, text=landmark_json + prompt)
       → delete file from Gemini Files API
       → { gloss, english, confidence }
  6. delete tmp file
  7. TTS + SeaweedFS audio save (unchanged)
  8. DB insert (unchanged)
  9. Write Redis result (unchanged)
```

### Landmark Sequence Format

Sampled every 3rd frame, normalized `(x, y, z)` coordinates per landmark:

```json
[
  {
    "frame": 0,
    "right": [[0.45, 0.62, 0.01], [0.44, 0.58, 0.02], "...21 points total"],
    "left":  [[0.55, 0.61, 0.01], "..."]
  },
  {
    "frame": 3,
    "right": [[0.46, 0.61, 0.01], "..."]
  }
]
```

`left` key is omitted if no left hand detected in that frame. At most ~300 sampled frames for a 30s 30fps clip.

### Gemini Prompt

```
You are an ASL sign language interpreter.

You are given:
1. A short video of a person performing an ASL sign
2. Hand landmark coordinates sampled every 3 frames (21 points per hand, normalized x/y/z)

Use both the visual motion in the video AND the landmark trajectory to identify the sign.

Landmark data:
{landmark_json}

Respond with ONLY valid JSON, no markdown:
{"gloss": "SIGN_NAME", "english": "English meaning", "confidence": 0.85}

Rules:
- gloss: the ASL sign in uppercase (e.g. "HELLO", "THANK_YOU")
- english: natural English translation
- confidence: 0.0 to 1.0
- If you cannot identify a clear sign: {"gloss": "UNKNOWN", "english": "Sign not recognised", "confidence": 0.0}
```

### Gemini Files API Call

```python
# Upload video (tmp file stays alive until this completes)
uploaded = await gemini_client.aio.files.upload(
    path=tmp_video_path,
    config={"mime_type": "video/mp4"}
)

# Recognise sign
response = await gemini_client.aio.models.generate_content(
    model="gemini-2.0-flash",
    contents=[
        types.Part.from_uri(file_uri=uploaded.uri, mime_type="video/mp4"),
        prompt_with_landmark_json,
    ]
)

# Delete from Google immediately — original stays in SeaweedFS
await gemini_client.aio.files.delete(name=uploaded.name)
```

---

## HandTracker Changes

**`models/handTracking.py`**

| | Current | New |
|---|---|---|
| Running mode | `RunningMode.IMAGE` | `RunningMode.VIDEO` |
| Return type | `tuple[str, bool]` — `(frame_b64, landmarks_found)` | `tuple[list[dict], bool]` — `(landmark_sequence, landmarks_found)` |
| Frame sampling | Every frame, keep best | Every 3rd frame, collect coordinates |
| Debug output | Annotated best frame PNG | Annotated best frame PNG (kept, from best landmark frame) |

New return value — `landmark_sequence` is `[]` if `landmarks_found` is `False`.

---

## InferenceService Changes

**`services/inference.py`**

Old:
```python
async def recognize_sign(self, frame_b64: str) -> dict:
```

New:
```python
async def recognize_sign(self, video_path: str, landmark_sequence: list[dict]) -> dict:
```

Internally: uploads video to Gemini Files API, generates with video + landmark JSON, deletes uploaded file, parses JSON response.

---

## Worker Changes

**`worker.py`**

- `HandTracker.process_video()` now returns `(landmark_sequence, landmarks_found)` instead of `(frame_b64, landmarks_found)`
- Early return on `not landmarks_found` — writes `NO_HAND` result to Redis, skips Gemini, TTS, and DB
- Temp file deletion moved to **after** `recognize_sign()` completes (was before)
- `recognize_sign()` call signature updated

---

## Modified Files

| File | Change |
|------|--------|
| `models/handTracking.py` | VIDEO mode, return landmark sequence |
| `services/inference.py` | `recognize_sign` uses Gemini Files API + landmark prompt |
| `worker.py` | NO_HAND early return, updated call signatures, temp file lifetime |

---

## Files NOT Changed

- All routers (`sign.py`, `speech.py`, `conversations.py`, etc.)
- All schemas
- `services/storage.py`
- `services/speech.py`
- `services/conversation.py`
- `main.py`, `server.py`
- Frontend — zero changes

---

## Error Handling

| Situation | Behaviour |
|-----------|-----------|
| No hands detected | `{ status: "done", gloss: "NO_HAND", english: "No hand detected — try again", confidence: 0.0 }` — no Gemini call |
| Video unreadable by OpenCV | `{ status: "error", detail: "No frames extracted from video" }` |
| Gemini Files API upload fails | `{ status: "error", detail: "Recognition service unavailable" }` |
| Gemini returns non-JSON | `{ gloss: "UNKNOWN", english: "Sign not recognised", confidence: 0.0 }` |
| Gemini file delete fails | Log warning only — does not affect result |

---

## Frontend

**Zero changes.** The API contract is identical:

- `POST /api/v1/sign/recognize` — same request
- `GET /api/v1/sign/result/{video_id}` — same response shape
- `NO_HAND` appears as `gloss: "NO_HAND"` with `status: "done"` — UI can check for this and show "No hand detected — try again" message using the existing `english` field

---

## What Is NOT in Scope

- Sending audio to Gemini alongside video
- Avatar / movement generation
- Multi-sign sentence recognition (single sign per clip)
- Streaming results from Gemini
