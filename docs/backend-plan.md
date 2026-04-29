# Backend Plan — Dave

FastAPI backend for ASL Bridge. See `docs/PLAN.md` for system architecture and API overview.

---

## Dev Setup (run without Docker)

**Prerequisites:** Python 3.11+, Docker Desktop running (for databases only)

**1. Start databases only (not the api container):**
```bash
docker compose up postgres redis seaweedfs-master seaweedfs-volume seaweedfs-filer -d
```

**2. Create and activate the virtual environment:**
```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
# or: .venv\Scripts\Activate.ps1  (PowerShell)
# or: source .venv/bin/activate   (Mac/Linux)
```

**3. Install dependencies:**
```bash
pip install -r requirements.txt
```

**4. Run migrations:**
```bash
PYTHONPATH=.. alembic upgrade head
```

**5. Run the server:**
```bash
PYTHONPATH=.. python server.py
# or: PYTHONPATH=.. uvicorn main:app --reload --port 8000
```

API docs at `http://localhost:8000/docs`

**Why `backend/.env` exists:**
The root `.env` uses Docker-internal hostnames (`postgres`, `redis`, `seaweedfs-filer`).
`backend/.env` overrides those to `localhost` so uvicorn on your laptop can reach the DBs.

**Debug frames:**
Processed frames are saved to `debug/frames/<video_id>.png` — what gets sent to Gemini.

---

## File Structure

```
backend/
├── main.py                      # FastAPI app factory, lifespan, routers
├── server.py                    # Uvicorn entrypoint
├── worker.py                    # ARQ worker (sign recognition + TTS + DB)
├── config/
│   ├── settings.py              # Pydantic Settings (loads .env)
│   ├── database.py              # Async SQLAlchemy engine + session
│   ├── redis.py                 # Redis connection pool
│   ├── gemini.py                # Gemini client factory
│   ├── elevenlabs.py            # ElevenLabs client factory
│   └── langfuse.py              # Langfuse observability client
├── db/
│   └── models.py                # SQLAlchemy ORM: Conversation + Message
├── migrations/
│   ├── env.py                   # Alembic async env
│   └── versions/
│       └── a1b2c3d4e5f6_add_conversations_messages.py
├── middleware/
│   └── request_logger.py        # JSON request/response logging
├── routers/
│   ├── health.py                # GET /api/v1/health
│   ├── uploads.py               # POST /api/v1/uploads/video
│   ├── sign.py                  # POST /api/v1/sign/recognize + GET /result/{id} + corrections
│   ├── speech.py                # POST /api/v1/speech/transcribe
│   └── conversations.py         # GET /api/v1/conversations/{session_id}/messages
├── schemas/
│   ├── sign.py                  # QueuedResponse, SignResultResponse, corrections
│   ├── speech.py                # TranscribeResponse
│   ├── conversation.py          # MessageItem, ConversationMessagesResponse
│   ├── upload.py                # UploadVideoResponse, UploadTextResponse
│   └── health.py                # HealthResponse
├── services/
│   ├── storage.py               # SeaweedFS upload + validation (unified save_bytes)
│   ├── inference.py             # Gemini: recognize_sign, gloss↔english
│   ├── speech.py                # ElevenLabs: transcribe (STT) + synthesize (TTS)
│   ├── conversation.py          # DB helpers: upsert_conversation, insert_message
│   └── collector.py             # JSONL auto-logging for inference + corrections
└── tests/
    ├── test_storage_audio.py
    ├── test_conversation_service.py
    └── test_conversations_router.py

models/                          # ML model files (project root, not inside backend/)
├── handTracking.py
└── hand_landmarker.task
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/uploads/video` | Upload video, store in SeaweedFS |
| POST | `/api/v1/sign/recognize` | Queue sign recognition job (ARQ) |
| GET | `/api/v1/sign/result/{video_id}` | Poll job result |
| POST | `/api/v1/sign/corrections` | Submit correction for a recognition |
| GET | `/api/v1/sign/corrections` | List recent corrections |
| POST | `/api/v1/speech/transcribe` | STT via ElevenLabs Scribe → transcript + gloss |
| GET | `/api/v1/conversations/{session_id}/messages` | Fetch full chat thread |

### Session ID

Both `POST /sign/recognize` and `POST /speech/transcribe` accept `X-Session-ID` header (optional UUID). If missing, the backend generates one. All messages from the same session are grouped into one `Conversation` row.

### Sign Result Shape

```json
{
  "api_version": "v1",
  "video_id": "...",
  "status": "done",
  "gloss": "HELLO",
  "english": "Hello",
  "confidence": 0.92,
  "landmarks_found": true,
  "audio_url": "http://<filer>/audio/<video_id>.mp3"
}
```

`audio_url` is `null` if TTS synthesis failed — recognition result is still returned.

### Conversation Messages Shape

```json
{
  "api_version": "v1",
  "conversation_id": "...",
  "total": 4,
  "messages": [
    {
      "id": "...",
      "direction": "deaf_to_hearing",
      "content": "Hello",
      "gloss": "HELLO",
      "audio_url": "http://<filer>/audio/<video_id>.mp3",
      "confidence": 0.92,
      "created_at": "2026-04-29T14:32:00Z"
    },
    {
      "id": "...",
      "direction": "hearing_to_deaf",
      "content": "How are you?",
      "gloss": "HOW YOU",
      "audio_url": null,
      "confidence": null,
      "created_at": "2026-04-29T14:32:18Z"
    }
  ]
}
```

---

## Worker Flow

The ARQ worker (`worker.py`) runs as a separate process:

```
process_sign_video(video_id, content_type, session_id):
  1. Download video from SeaweedFS
  2. HandTracker.process_video() → best frame (base64) + landmarks_found
  3. Gemini → { gloss, english, confidence }
  4. ElevenLabs TTS(english) → audio_bytes
  5. save_bytes(audio_bytes, video_id, folder="audio", ext="mp3") → audio_url
  6. upsert_conversation(session_id) + insert_message(deaf_to_hearing)
  7. Write Redis result: { status, gloss, english, confidence, landmarks_found, audio_url }
```

---

## Storage

`services/storage.py` — one `save_bytes()` function for all media:

```python
# Video (default)
await save_bytes(contents, file_id, "video/mp4")
# → SeaweedFS /videos/{file_id}.mp4

# TTS audio
await save_bytes(audio_bytes, video_id, "audio/mpeg", folder="audio", ext="mp3")
# → SeaweedFS /audio/{video_id}.mp3
```

---

## Database

Two tables — `conversations` (one per session) and `messages` (many per conversation):

- `direction`: `"deaf_to_hearing"` | `"hearing_to_deaf"`
- `user_id` on `conversations` is nullable — populated when auth is added
- Messages ordered by `created_at ASC` for chat thread rendering

---

## What's Done ✓

- Health, uploads, sign recognition, speech transcribe, corrections endpoints
- ARQ worker queue with async sign recognition
- ElevenLabs TTS synthesis + audio saved to SeaweedFS
- Conversation + message persistence (session-based, auth-ready)
- `GET /api/v1/conversations/{session_id}/messages` chat history endpoint
- Observability: JSON logs, Prometheus metrics, Langfuse LLM tracing
- All routers use `Annotated` params + return type annotations (FastAPI skill compliant)

---

## What's Left [ ]

- [ ] Auth (user accounts) — `user_id` column on `conversations` is ready, just needs a users table + JWT middleware
- [ ] Video optimization — send short video + landmark motion data directly to Gemini (replaces single-frame approach)
- [ ] Run `alembic upgrade head` in CI / Docker entrypoint
- [ ] Wire tests into Docker Compose for CI
