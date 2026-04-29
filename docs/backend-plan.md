# Backend Plan — Dave

FastAPI backend for ASL Bridge. See `docs/PLAN.md` for system architecture and API overview.

---

## File Structure

```
backend/
├── main.py
├── routers/
│   ├── health.py      # GET /api/v1/health
│   ├── asl.py         # POST /api/v1/asl/recognize, /corrections
│   ├── speech.py      # POST /api/v1/speech/transcribe
│   └── dataset.py     # GET /api/v1/dataset/stats
├── services/
│   ├── video.py       # OpenCV preprocessing (Bob)
│   ├── inference.py   # Gemini 3.1 Pro + Flash-Lite calls
│   ├── speech.py      # ElevenLabs STT + TTS
│   └── collector.py   # JSONL auto-logging
├── models/            # Pydantic request/response schemas
├── uploads/           # Saved video/audio files (Docker volume)
├── data/
│   └── raw/           # JSONL training data (Docker volume)
├── requirements.txt
├── .env.example
├── Dockerfile
└── docker-compose.yml
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

## Tasks

### Setup
- [ ] Scaffold folder structure
- [ ] `requirements.txt` — fastapi, uvicorn, python-multipart, opencv-python, google-genai, elevenlabs, aiofiles, python-dotenv
- [ ] `.env.example` with all required keys (`GEMINI_API_KEY`, `ELEVENLABS_API_KEY`)
- [ ] `Dockerfile` — Python 3.11 slim, copy requirements, install, expose 8000
- [ ] `docker-compose.yml` — service + volumes for `uploads/` and `data/raw/`
- [ ] `main.py` — app factory, register routers, CORS middleware (allow all in dev)

### Health router (`routers/health.py`)
- [ ] `GET /api/v1/health`
  - Return `{ api_version, status, uptime, keys_set: { gemini, elevenlabs } }`

### ASL router (`routers/asl.py`)
- [ ] `POST /api/v1/asl/recognize`
  - Accept `video: UploadFile`
  - Validate content type (video/mp4, video/quicktime)
  - Save to `uploads/{uuid}.mp4`
  - Call `services/video.py` → preprocessed frame
  - Call `services/inference.py` → gloss + English + confidence
  - Call `services/collector.py` → log to JSONL
  - Return `{ api_version, gloss, english, confidence, video_id }`
- [ ] `POST /api/v1/asl/corrections`
  - Accept `{ video_id, correct_gloss, notes? }`
  - Append to `data/raw/corrections.jsonl`
  - Return `{ api_version, id, saved: true }`
- [ ] `GET /api/v1/asl/corrections`
  - Read `data/raw/corrections.jsonl`
  - Return `{ api_version, total, recent[] }`

### Speech router (`routers/speech.py`)
- [ ] `POST /api/v1/speech/transcribe`
  - Accept `audio: UploadFile`
  - Save to `uploads/{uuid}.m4a`
  - Call `services/speech.py` → ElevenLabs Scribe → English transcript
  - Call `services/inference.py` → Gemini Flash-Lite → ASL gloss
  - Return `{ api_version, transcript, gloss }`

### Dataset router (`routers/dataset.py`)
- [ ] `GET /api/v1/dataset/stats`
  - Count lines in `data/raw/*.jsonl`
  - Return `{ api_version, total_samples, corrections, last_updated }`

### Services
- [ ] `services/video.py` (Bob owns, Dave integrates)
  - Input: video file path
  - Output: base64-encoded best frame
- [ ] `services/inference.py`
  - `recognize_sign(frame_b64)` → Gemini 3.1 Pro → `{ gloss, confidence }`
  - `gloss_to_english(gloss)` → Gemini 3.1 Flash-Lite → English string
  - `english_to_gloss(text)` → Gemini 3.1 Flash-Lite → gloss string
- [ ] `services/speech.py`
  - `transcribe(audio_path)` → ElevenLabs Scribe → English string
  - `synthesize(text)` → ElevenLabs TTS → audio bytes (for future use)
- [ ] `services/collector.py`
  - `log_inference(video_id, frame_b64, gloss, confidence, timestamp)` → append JSONL

### Models (`models/`)
- [ ] `BaseResponse` — `{ api_version: "v1" }`
- [ ] `RecognizeResponse(BaseResponse)` — `{ gloss, english, confidence, video_id }`
- [ ] `CorrectionRequest` — `{ video_id, correct_gloss, notes? }`
- [ ] `CorrectionResponse(BaseResponse)` — `{ id, saved }`
- [ ] `CorrectionsListResponse(BaseResponse)` — `{ total, recent[] }`
- [ ] `TranscribeResponse(BaseResponse)` — `{ transcript, gloss }`
- [ ] `DatasetStatsResponse(BaseResponse)` — `{ total_samples, corrections, last_updated }`
- [ ] `HealthResponse(BaseResponse)` — `{ status, uptime, keys_set }`

---

## Notes

- Everything returns text for now — no binary/video responses yet
- All file I/O must be async (`aiofiles`) — no blocking calls in async routes
- Business logic stays in `services/`, routers just validate + delegate
- Confidence threshold: if `confidence < 0.6` set `gloss = "signing..."` in response
- Two API keys only: `GEMINI_API_KEY` and `ELEVENLABS_API_KEY`
