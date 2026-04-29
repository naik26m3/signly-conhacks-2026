# ASL Bridge — Team Plan

> "No special request. No interpreter. No aid. Just talk."

**Team:** Kai · Bob · Max · Dave  
**Duration:** 36-hour hackathon  
**Target latency:** < 2 seconds end-to-end  
**Platform:** iOS + Android (Expo Go), Backend on homelab/VPS

---

## Mission

70 million deaf people use sign language as their first language. ASL Bridge removes the communication barrier entirely — deaf users sign naturally, hearing users speak naturally, the app handles everything in between in real time.

---

## Team & Ownership

| Person | Role | Owns |
|---|---|---|
| Kai | Frontend | Expo app, camera UI, audio recording, ElevenLabs TTS |
| Bob | Computer Vision | OpenCV preprocessing pipeline (`services/video.py`) |
| Max | UI/UX | Design system, two-mode layout, confidence indicator |
| Dave | Backend + Models | FastAPI, vision API calls, ElevenLabs STT, data collection |

Detailed task breakdowns → `docs/backend-plan.md` · `docs/frontend-plan.md`

---

## System Architecture

### Path 1 — Deaf → Hearing
```
Front Camera
  → Video upload → POST /api/v1/asl/recognize
  → OpenCV: extract frames, resize, CLAHE, HSV mask, ROI crop
  → Gemini 3.1 Pro → ASL gloss
  → Gemini 3.1 Flash-Lite → natural English
  → ElevenLabs TTS → speaks aloud to hearing person
```

### Path 2 — Hearing → Deaf
```
Microphone
  → Audio upload → POST /api/v1/speech/transcribe
  → ElevenLabs STT (Scribe) → English text
  → Gemini 3.1 Flash-Lite → ASL gloss
  → Large gloss text displayed on screen
```

### Data Collection (silent, every inference)
```
Every inference → JSONL saved to data/raw/
Human corrections → POST /api/v1/asl/corrections
Accumulated dataset → post-hackathon fine-tune (Phase 4)
```

---

## API Endpoints

All endpoints versioned under `/api/v1/`. Swagger at `/docs`, spec at `/openapi.json`.

Every response includes `api_version: "v1"` so clients always know what version they are talking to.

### Health

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/health` | Service status and API key availability |

### ASL

| Method | Endpoint | Body | Returns |
|---|---|---|---|
| POST | `/api/v1/asl/recognize` | `multipart/form-data` — `video: File` | `{ api_version, gloss, english, confidence, video_id }` |
| POST | `/api/v1/asl/corrections` | `{ video_id, correct_gloss, notes? }` | `{ api_version, id, saved }` |
| GET | `/api/v1/asl/corrections` | — | `{ api_version, total, recent[] }` |

### Speech

| Method | Endpoint | Body | Returns |
|---|---|---|---|
| POST | `/api/v1/speech/transcribe` | `multipart/form-data` — `audio: File` | `{ api_version, transcript, gloss }` |

### Dataset

| Method | Endpoint | Returns |
|---|---|---|
| GET | `/api/v1/dataset/stats` | `{ api_version, total_samples, corrections, last_updated }` |

---

## Tech Stack

### Hackathon

| Layer | Tool |
|---|---|
| Frontend | Expo React Native + Expo Go |
| STT | ElevenLabs Scribe API |
| TTS | ElevenLabs API |
| Backend | FastAPI + Python 3.11 |
| Computer Vision | OpenCV |
| ASL Vision Model | Gemini 3.1 Pro |
| Gloss ↔ English translation | Gemini 3.1 Flash-Lite |
| Containerization | Docker + docker-compose |

### Post-Hackathon

| Phase | Layer | Tool |
|---|---|---|
| Phase 2 | Signing avatar output | Wan 2.6 via FAL.AI |
| Phase 3 | Multi-language SL | SignLLM + Prompt2Sign |
| Phase 3 | User accounts | TBD |
| Phase 4 | ASL fine-tune (last step) | Qwen3-VL 7B LoRA |

---

## Hackathon Timeline

### Hours 0–6 — Foundation
- Dave: FastAPI scaffold, `/health`, `/asl/recognize` mock response
- Kai: Expo setup, camera UI, POST to backend
- Bob: OpenCV pipeline on static images
- Max: Design system handed to Kai

### Hours 6–16 — Core Features
- Dave: Real Gemini call, ElevenLabs STT, JSONL logging
- Bob: Integrate OpenCV into recognize endpoint
- Kai: Real response display, mic recording, ElevenLabs TTS
- Max: Confidence indicator, demo polish

### Hours 16–28 — Integration + Polish
- Full pipeline test end-to-end
- Latency measurement and optimization
- Bug fixes, edge cases

### Hours 28–34 — Demo Prep
- Practice 10–15 demo signs
- Stress test 20+ runs
- Record backup video

### Hours 34–36 — Buffer
- Bug fixes only

---

## Demo Script

**Signs:** HELLO, THANK YOU, YES, NO, HELP, WATER, NAME, PLEASE, SORRY, UNDERSTAND

1. Show two-mode UI
2. Dave signs HELLO → app speaks aloud → judge responds
3. App transcribes → shows gloss → Dave signs back
4. 2–3 more exchanges
5. Show `/api/v1/dataset/stats` — training samples collected live during demo

---

## Post-Hackathon Roadmap

**Phase 2** — Signing avatar: replace gloss text with Wan 2.6 video output via FAL.AI  
**Phase 3** — Multi-language: Chinese SL, European SL via SignLLM + Prompt2Sign  
**Phase 4** — Fine-tune ASL recognition with Qwen3-VL 7B LoRA (only after enough data)

---

## Environment Variables

```env
GEMINI_API_KEY=        # Gemini 3.1 Pro (ASL vision) + Flash-Lite (translation)
ELEVENLABS_API_KEY=    # STT (Scribe) + TTS
```

---

*Last updated: April 2026 — Dave*
