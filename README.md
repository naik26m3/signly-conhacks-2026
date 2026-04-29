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

## API keys needed

| Key | Where to get it | Used for |
|---|---|---|
| `GEMINI_API_KEY` | aistudio.google.com | Primary ASL vision model |
| `GROQ_API_KEY` | console.groq.com | Whisper STT + Llama translation |
| `OPENAI_API_KEY` | platform.openai.com | GPT-4o mini fallback vision |

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
