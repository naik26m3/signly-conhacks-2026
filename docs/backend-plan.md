# Backend Plan — Dave

FastAPI backend for ASL Bridge. See `docs/PLAN.md` for system architecture and API overview.

---

## Dev Setup (run without Docker)

**Prerequisites:** Python 3.11+, Docker Desktop running (for databases only)

**1. Start databases only (not the api container):**
```bash
docker compose up postgres redis seaweedfs-master seaweedfs-volume seaweedfs-filer -d
```

**2. Create and activate the virtual environment (first time only):**
```bash
cd backend
python -m venv .venv

# Windows (Git Bash / bash)
source .venv/Scripts/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

**3. Install dependencies (first time only):**
```bash
pip install -r requirements.txt
```

**4. Run the server:**
```bash
PYTHONPATH=.. python server.py
# or: PYTHONPATH=.. uvicorn main:app --reload --port 8000
```

API will be at `http://localhost:8000` — docs at `http://localhost:8000/docs`

**Why `backend/.env` exists:**
The root `.env` uses Docker-internal hostnames (`postgres`, `redis`, `seaweedfs-filer`).
`backend/.env` overrides just those 3 URLs to `localhost` so uvicorn on your laptop can reach the DBs.
Everything else (API keys etc.) still comes from the root `.env`.

**Debug frames:**
When a video is processed, the best hand-landmark frame is saved to `debug/frames/<video_id>.png`
so you can see exactly what gets sent to Gemini.

---

## File Structure

```
backend/
├── main.py                  # App entry point (imports server.py)
├── server.py                # App factory, routers, CORS, middleware
├── config/
│   ├── settings.py          # Pydantic Settings (loads .env)
│   ├── database.py          # Async SQLAlchemy connection pool
│   └── redis.py             # Redis connection pool
├── middleware/
│   └── request_logger.py    # Request/response logging
├── migrations/
│   └── env.py               # Alembic migration env
├── routers/
│   ├── health.py            # GET /api/v1/health  ✓
│   ├── uploads.py           # POST /api/v1/uploads/video  ✓
│   ├── sign.py              # POST /api/v1/sign/recognize  [ ]
│   └── speech.py            # POST /api/v1/speech/transcribe  [ ]
└── services/
    ├── storage.py           # SeaweedFS upload + validation  ✓
    ├── video.py             # OpenCV frame extraction  [ ]
    ├── inference.py         # Gemini model calls  [ ]
    ├── speech.py            # ElevenLabs STT + TTS  [ ]
    └── collector.py         # JSONL auto-logging  [ ]

models/                      # ML model files (root level, not inside backend/)
├── handTracking.py
└── hand_landmarker.task
```

---

## Standard Response Shape

Every endpoint returns `api_version` so clients always know what version responded.

```python
class BaseResponse(BaseModel):
    api_version: str = "v1"
```

All response models inherit from `BaseResponse`.

---

## What's Done ✓

- Health endpoint: `GET /api/v1/health`
- Video upload endpoint: `POST /api/v1/uploads/video`
  - Validates MIME type + ISO-BMFF/WebM magic bytes
  - Stores to SeaweedFS via `services/storage.py`
  - Returns `{ api_version, video_id, status }`
- Config layer: settings, DB pool, Redis pool
- Request logger middleware
- Alembic migrations scaffold

---

## What's Left [ ]

### Sign router (`routers/sign.py`)
- [ ] `POST /api/v1/sign/recognize`
  - Accept `video_id` (already uploaded) or `video: UploadFile`
  - Call `services/video.py` → best frame (base64)
  - Call `services/inference.py` → gloss + English + confidence
  - Call `services/collector.py` → log to JSONL
  - Return `{ api_version, gloss, english, confidence, video_id }`
- [ ] `POST /api/v1/sign/corrections`
  - Accept `{ video_id, correct_gloss, notes? }`
  - Append to `data/raw/corrections.jsonl`
  - Return `{ api_version, id, saved: true }`

### Speech router (`routers/speech.py`)
- [ ] `POST /api/v1/speech/transcribe`
  - Accept `audio: UploadFile`
  - Save via `services/storage.py`
  - Call `services/speech.py` → ElevenLabs Scribe → English transcript
  - Call `services/inference.py` → Gemini Flash-Lite → ASL gloss
  - Return `{ api_version, transcript, gloss }`

### Services
- [ ] `services/video.py` — extract best frame from video → base64
- [ ] `services/inference.py`
  - `recognize_sign(frame_b64)` → Gemini → `{ gloss, confidence }`
  - `gloss_to_english(gloss)` → Gemini Flash-Lite → English string
  - `english_to_gloss(text)` → Gemini Flash-Lite → gloss string
- [ ] `services/speech.py`
  - `transcribe(audio_path)` → ElevenLabs Scribe → English string
  - `synthesize(text)` → ElevenLabs TTS → audio bytes
- [ ] `services/collector.py`
  - `log_inference(video_id, frame_b64, gloss, confidence, timestamp)` → JSONL

### Pydantic schemas (add to `server.py` or a `schemas/` module)
- [ ] `RecognizeResponse(BaseResponse)` — `{ gloss, english, confidence, video_id }`
- [ ] `CorrectionRequest` — `{ video_id, correct_gloss, notes? }`
- [ ] `TranscribeResponse(BaseResponse)` — `{ transcript, gloss }`

---

## Notes

- Business logic stays in `services/`, routers just validate + delegate
- Confidence threshold: if `confidence < 0.6` set `gloss = "signing..."` in response
- Two API keys: `GEMINI_API_KEY` and `ELEVENLABS_API_KEY` (in root `.env`)
- All file I/O must be async — no blocking calls in async routes
