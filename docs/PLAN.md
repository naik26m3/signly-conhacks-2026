# ASL Bridge — Team Plan

> "No special request. No interpreter. No aid. Just talk."

**Team:** Kai · Bob · Max · Dave  
**Duration:** 36-hour hackathon  
**Target latency:** < 2 seconds end-to-end  
**Platform:** iOS + Android (Expo Go), Backend on homelab/VPS

---

## 1. Mission

70 million deaf people use sign language as their first language. ASL Bridge removes the communication barrier entirely — deaf users sign naturally, hearing users speak naturally, the app handles everything in between in real time.

---

## 2. Team & Ownership

### Kai — Frontend (React Native)
- Expo React Native app setup (cross-platform, no Mac needed)
- Camera feed UI — live preview with start/stop signing button
- Throttled frame capture → send to backend at ~1 frame/sec
- Display gloss + English translation on screen
- Hearing path: mic record button → send audio to backend
- Show gloss response in large readable text for deaf user
- expo-speech TTS integration (speaks aloud to hearing person)

### Bob — Computer Vision (OpenCV)
- `services/video.py` — full OpenCV preprocessing pipeline
- Decode base64 frame → resize to 640×480
- CLAHE brightness normalization (handles bad/variable lighting)
- Horizontal flip correction for front camera
- Skin-tone HSV mask → hand contour extraction
- Crop ROI with padding → re-encode to base64
- Return processed frame ready for vision API

### Max — UI/UX Design
- Design system: colors, typography, component specs
- Two-mode layout: Deaf Mode (camera + large text) and Hearing Mode (mic + TTS)
- Confidence indicator — "signing..." state vs confirmed gloss
- Demo screen layout optimized for judges (clear, impressive at a glance)
- Dark mode first — works in any lighting during demo

### Dave — Backend + Model Quality
- FastAPI backend scaffold: `main.py` + routers (`asl`, `speech`, `finetune`, `health`)
- Benchmark vision models: Gemini 2.0 Flash vs GPT-4o mini on demo signs
- Prompt engineering for zero-shot ASL recognition (few-shot reference images)
- `services/inference.py` — LLM calls (gloss→English, English→gloss)
- Groq integration: Whisper large-v3 STT + Llama 3.1 8B text translation
- `services/collector.py` — auto-log every inference as JSONL for future fine-tune
- `POST /asl/correct` — human correction endpoint for high-quality training labels

---

## 3. System Architecture

### Path 1 — Deaf → Hearing
```
Front Camera
  → Base64 frame (Kai)
  → OpenCV preprocessing (Bob): resize, CLAHE, HSV mask, ROI crop
  → Vision model (Dave): Gemini 2.0 Flash → ASL gloss
  → Llama 3.1 8B (Groq): gloss → natural English
  → expo-speech TTS (Kai): speaks aloud to hearing person
```

### Path 2 — Hearing → Deaf
```
Microphone (Kai)
  → Audio file → POST /speech/translate (Dave)
  → Whisper large-v3 (Groq): audio → English text
  → Llama 3.1 8B (Groq): English → ASL gloss
  → Large gloss text displayed on screen (Kai + Max)
```

### Data Collection (runs silently on every inference)
```
Every inference → auto-saved to data/raw/ as JSONL (frame + label + timestamp)
Human corrections via /asl/correct → high-quality labeled samples
Accumulated dataset → post-hackathon Qwen3-VL fine-tune
```

---

## 4. API Endpoints

| Method | Endpoint | Owner | Description |
|---|---|---|---|
| POST | `/asl/recognize` | Dave + Bob | base64 frame → gloss + English |
| POST | `/asl/correct` | Dave | human correction → training label |
| POST | `/speech/translate` | Dave | audio file → English + gloss |
| GET | `/finetune/stats` | Dave | dataset collection progress |
| GET | `/health` | Everyone | backend status check |

---

## 5. Tech Stack

### Hackathon (now)
| Layer | Tool | Cost |
|---|---|---|
| Frontend | Expo React Native + Expo Go | Free |
| TTS | expo-speech (on-device) | Free |
| Backend | FastAPI + Python 3.11 | Free |
| Computer Vision | OpenCV | Free |
| ASL Vision Model | Gemini 2.0 Flash | ~free tier |
| STT | Whisper large-v3 via Groq | Free |
| Text/Gloss LLM | Llama 3.1 8B via Groq | Free |
| Fallback Vision | GPT-4o mini (OpenAI) | Paid |

### Post-Hackathon
| Layer | Tool | Notes |
|---|---|---|
| ASL Recognition | Qwen3-VL (fine-tuned) | Replaces zero-shot |
| Fine-tune infra | Colab Pro or RunPod A100 | ~$10-15 for 6-8h |
| Signing avatar output | Wan 2.6 (open source, Apache 2.0) | Via FAL.AI API |
| Multi-language SL | SignLLM + Prompt2Sign dataset | ASL + 7 other SLs |
| User accounts | To be designed | Sign-up, avatars, prefs |

---

## 6. Hackathon Timeline (36 hours)

### Hours 0–6 — Foundation (everyone unblocked)
**Dave:**
- Scaffold FastAPI project structure
- Implement `/health` endpoint
- Implement `/asl/recognize` returning mock data (so Kai can integrate immediately)
- Implement `/speech/translate` skeleton with Groq Whisper

**Kai:**
- Expo project setup
- Camera feed UI working
- Frame capture → HTTP POST to backend (even with mock response)

**Bob:**
- OpenCV pipeline in `services/video.py`
- Test preprocessing on static images first

**Max:**
- Design system ready: colors, fonts, component specs
- Share with Kai to implement

---

### Hours 6–16 — Core Features
**Dave:**
- Replace mock with real Gemini 2.0 Flash vision call
- Run model benchmark: Gemini vs GPT-4o mini on 10 demo signs
- Build best few-shot prompt using reference sign images
- Wire up Llama 3.1 8B for gloss↔English translation
- Implement `services/collector.py` for JSONL logging

**Bob:**
- Integrate OpenCV pipeline into `/asl/recognize` endpoint
- Test with real camera frames from Kai

**Kai:**
- Display real gloss + English response from backend
- Implement mic recording → `/speech/translate`
- Display gloss text response on screen (large, readable)
- Wire up expo-speech TTS

**Max:**
- Build confidence indicator component ("signing..." state)
- Demo screen layout polish

---

### Hours 16–28 — Integration + Polish
- Full pipeline test: sign → backend → TTS (all 4 together)
- Measure real end-to-end latency, optimize if over 2s
- Add client-side 1 frame/sec throttle if not done
- Add confidence threshold: show "signing..." if model unsure
- Fix bugs, edge cases, bad lighting handling

---

### Hours 28–34 — Demo Prep
- Practice the exact demo conversation (10–15 specific signs)
- Stress test: run pipeline 20+ times, check for failures
- Prepare fallback: if live demo breaks, have a recorded backup video ready
- Make sure `/finetune/stats` shows collected data count (impressive to judges)

---

### Hours 34–36 — Buffer
- Bug fixes only, no new features
- Rest before demo

---

## 7. Demo Script (Live)

Dave learns these specific signs for the live demo:

**Suggested vocab (visually distinct, single-handed where possible):**
HELLO, THANK YOU, YES, NO, HELP, WATER, NAME, PLEASE, SORRY, UNDERSTAND

**Demo flow:**
1. Open app, show two-mode UI (Max's design)
2. Dave signs HELLO → app speaks "Hello" aloud → hearing judge responds "Hi, what's your name?"
3. App transcribes speech → shows "YOUR NAME WHAT?" in gloss on screen → Dave reads and signs back
4. Repeat 2-3 more exchanges
5. Show `/finetune/stats` — "we've already collected X training samples during this demo"

**Key talking point for judges:** Every interaction during the demo is automatically building our training dataset for a specialized ASL model. The app gets smarter the more it's used.

---

## 8. Key Risks & Mitigations

### Risk 1 — Zero-shot model quality on ASL is poor
**Why it happens:** Gemini and GPT-4o mini are general vision models, not trained on sign language.  
**Mitigation:**
- Dave benchmarks both models in first 6 hours
- Constrain demo to 10–15 specific signs
- Use few-shot reference images in the prompt (acts like lightweight fine-tuning)
- Set confidence threshold — show "signing..." instead of wrong word

### Risk 2 — Latency over 2 seconds
**Why it happens:** 4-5 network hops: camera → backend → OpenCV → vision API → LLM → TTS  
**Mitigation:**
- Run backend on homelab (eliminates cloud round-trip latency)
- Use Groq for Whisper + Llama (fastest free inference available)
- Client-side throttle at 1 frame/sec
- Skip frames with no hand motion detected

### Risk 3 — Wrong translation spoken aloud during demo
**Why it happens:** Zero-shot model hallucinates on unclear frames  
**Mitigation:**
- Practice exact demo signs until confident
- Confidence threshold hides bad predictions
- Have 1-2 "safe" signs that always work as demo backup

### Risk 4 — API rate limits / cost
**Why it happens:** Vision APIs are expensive at high frequency  
**Mitigation:**
- Gemini free tier is generous enough for a 36h hackathon
- 1 frame/sec throttle limits total API calls
- GPT-4o mini as paid fallback if Gemini has issues

---

## 9. Post-Hackathon Roadmap

### Phase 2 — Fine-tune ASL Recognition (Week 1-2 after)
- Export JSONL collected during hackathon
- Add How2Sign dataset (ASL, ~80 hours of video)
- Fine-tune Qwen3-VL 7B with LoRA on Colab Pro or RunPod A100 (~6-8h, ~$10-15)
- Use `2U1/Qwen-VL-Series-Finetune` repo (HuggingFace + Liger-Kernel)
- Replace Gemini zero-shot with fine-tuned model in production

### Phase 3 — Signing Avatar Video Output (Month 1-3)
- Replace gloss text display with a signing avatar video
- Use Wan 2.6 (open source, Apache 2.0) via FAL.AI API ($0.05/sec)
- Reference-to-video: upload avatar reference image → generate signing clips
- Target: hearing person speaks → deaf user sees a person signing back to them

### Phase 4 — Multi-Language + Full Product (Month 3+)
- Expand to Chinese SL, European SL using SignLLM + Prompt2Sign dataset (8 sign languages)
- User accounts, sign-up flow, custom signing avatars
- Fine-tuned models per sign language
- OpenAI-compatible fine-tune API for serving specialized models

---

## 10. File Structure

```
asl-bridge/
├── main.py
├── routers/
│   ├── asl.py          # /asl/recognize, /asl/correct
│   ├── speech.py       # /speech/translate
│   ├── finetune.py     # /finetune/stats
│   └── health.py       # /health
├── services/
│   ├── video.py        # OpenCV preprocessing pipeline (Bob)
│   ├── inference.py    # Vision + LLM API calls (Dave)
│   └── collector.py    # JSONL auto-logging (Dave)
├── data/
│   └── raw/            # Auto-saved frames + labels (JSONL)
├── requirements.txt
└── .env                # API keys (OpenAI, Groq, Gemini)
```

---

## 11. Environment Setup

### API Keys needed
- `OPENAI_API_KEY` — GPT-4o mini fallback vision
- `GROQ_API_KEY` — Whisper STT + Llama 3.1 8B (free)
- `GEMINI_API_KEY` — Primary vision model (free tier)

### Backend
```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install fastapi uvicorn opencv-python openai groq google-generativeai python-dotenv
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
npx create-expo-app asl-bridge
cd asl-bridge
npx expo install expo-camera expo-av expo-speech
npx expo start
```

---

*Last updated: April 2026 — Dave*
