# ASL Bridge

Real-time ASL ↔ English communication app built at ConHacks 2026.

Deaf users sign naturally, hearing users speak naturally — the app handles everything in between in under 2 seconds.

---

## Quick start

### Clone (includes skill submodules)
```bash
git clone --recurse-submodules https://github.com/naik26m3/signly-conhacks-2026
```

If you already cloned without `--recurse-submodules`:
```bash
git submodule update --init --recursive
```

### Backend
```bash
cd backend
cp .env.example .env        # add your API keys
docker compose up --build
```

API runs at `http://localhost:8000`
Swagger docs at `http://localhost:8000/docs`
OpenAPI spec at `http://localhost:8000/openapi.json`

### Frontend
```bash
cd frontend
npm install
npx expo start
```

Scan the QR code with Expo Go on your phone.

---

## How it works

**Deaf → Hearing:** User records a short ASL sign (H.264, 480p, max 30s). The backend runs MediaPipe HandLandmarker in VIDEO mode to extract a 21-point landmark sequence sampled every 3rd frame. The video and landmark data are sent together to Gemini via the Files API — Gemini uses both the visual motion and the spatial trajectory to identify the sign. The result is read aloud to the hearing person via ElevenLabs TTS.

**Hearing → Deaf:** Hearing person speaks. ElevenLabs Scribe transcribes the audio to text. The transcript is displayed in large readable text on the deaf user's screen and converted to ASL gloss.

All past turns are stored per-session and accessible as a chat history.

---

## API keys needed

| Key | Where to get it | Used for |
|---|---|---|
| `GEMINI_API_KEY` | aistudio.google.com | ASL video recognition (Files API + landmark prompt) |
| `ELEVENLABS_API_KEY` | elevenlabs.io | TTS (deaf→hearing audio) + Scribe STT (hearing→deaf) |

---

## Docs

- `agents.md` — agent guide: frontend + backend conventions, AI models, how to work in this repo
- `docs/PLAN.md` — full system architecture, team ownership, API endpoints, 36h timeline
- `skills/expo-skills/` — Expo official agent skills (submodule)
- `skills/callstack-skills/` — Callstack React Native agent skills (submodule)
- `skills/fastapi/` — FastAPI full source + docs (submodule)

---

## Team

Kai · Bob · Max · Dave — 36-hour hackathon
