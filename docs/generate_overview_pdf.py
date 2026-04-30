"""Generate docs/overview.pdf — ASL Bridge hackathon submission overview.

Run:  python docs/generate_overview_pdf.py
Out:  docs/overview.pdf  (15-16 pages)
"""
from pathlib import Path
from fpdf import FPDF

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
DESIGN = ROOT / "design"
OUT = DOCS / "overview.pdf"

# ── palette (from frontend/app/*.jsx) ──────────────────────────────────────
BROWN_DARK = (67, 40, 24)        # #432818
BROWN_MID = (107, 69, 47)        # secondary headings
TAN = (253, 240, 208)            # #FDF0D0 (cover accent)
BG_CREAM = (249, 246, 241)       # #F9F6F1
RULE = (224, 216, 204)           # #e0d8cc
MUTED = (160, 152, 128)          # #a09880
INK = (44, 44, 46)               # body text
CODE_BG = (244, 240, 232)


class PDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=15)
        self.set_margins(left=18, top=15, right=18)
        self.alias_nb_pages()

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-15)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 8, f"ASL Bridge - ConHacks 2026   -   Page {self.page_no()} / {{nb}}",
                  align="C")

    # ── primitives ─────────────────────────────────────────────────────────
    def h1(self, text):
        self.ln(1)
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(*BROWN_DARK)
        self.cell(0, 9, text, ln=1)
        self.set_draw_color(*BROWN_DARK)
        self.set_line_width(0.6)
        y = self.get_y()
        self.line(self.l_margin, y, self.l_margin + 28, y)
        self.ln(3)

    def h2(self, text):
        self.ln(1.5)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*BROWN_DARK)
        self.cell(0, 6, text, ln=1)
        self.ln(0.5)

    def h3(self, text):
        self.set_font("Helvetica", "B", 10.5)
        self.set_text_color(*BROWN_MID)
        self.cell(0, 5.5, text, ln=1)

    def body(self, text, size=9.5):
        self.set_font("Helvetica", "", size)
        self.set_text_color(*INK)
        self.multi_cell(0, 4.5, text)
        self.ln(0.8)

    def bullets(self, items, size=9.5):
        self.set_font("Helvetica", "", size)
        self.set_text_color(*INK)
        for it in items:
            y = self.get_y()
            self.set_xy(self.l_margin, y)
            self.cell(4.5, 4.5, chr(183))  # bullet
            self.set_x(self.l_margin + 4.5)
            self.multi_cell(0, 4.5, it)
        self.ln(0.4)

    def code(self, text, size=8.0):
        # Pseudo "code block" — boxed monospace.
        self.set_font("Courier", "", size)
        self.set_fill_color(*CODE_BG)
        self.set_text_color(40, 40, 40)
        line_h = 3.6
        for line in text.splitlines() or [""]:
            self.cell(0, line_h, " " + line, ln=1, fill=True)
        self.ln(1.5)
        self.set_text_color(*INK)

    def kv_table(self, rows, col1=52):
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(*INK)
        page_w = self.w - self.l_margin - self.r_margin
        col2 = page_w - col1
        for k, v in rows:
            y0 = self.get_y()
            self.set_font("Helvetica", "B", 9.5)
            self.multi_cell(col1, 4.6, k, border=0)
            y_after_k = self.get_y()
            self.set_xy(self.l_margin + col1, y0)
            self.set_font("Helvetica", "", 9.5)
            self.multi_cell(col2, 4.6, v, border=0)
            y_after_v = self.get_y()
            self.set_y(max(y_after_k, y_after_v))
            # thin separator
            self.set_draw_color(*RULE)
            self.set_line_width(0.15)
            self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
            self.ln(1.2)

    def callout(self, label, text):
        # Tan banner with bold label — for "Why this matters" / quotes.
        page_w = self.w - self.l_margin - self.r_margin
        x0, y0 = self.get_x(), self.get_y()
        self.set_fill_color(*TAN)
        # Pre-compute height
        self.set_font("Helvetica", "", 9.5)
        n_lines = self.multi_cell(page_w - 6, 4.5, text, split_only=True)
        h = max(11, len(n_lines) * 4.5 + 7)
        self.rect(x0, y0, page_w, h, style="F")
        self.set_xy(x0 + 3, y0 + 1.5)
        self.set_text_color(*BROWN_DARK)
        self.set_font("Helvetica", "B", 9.5)
        self.cell(0, 4.5, label, ln=1)
        self.set_xy(x0 + 3, y0 + 6)
        self.set_text_color(*INK)
        self.set_font("Helvetica", "", 9.5)
        self.multi_cell(page_w - 6, 4.5, text)
        self.set_y(y0 + h + 2)


def safe(text):
    """Map non-Latin1 typographic characters fpdf's core fonts can't render."""
    return (
        text.replace("—", "-")
            .replace("–", "-")
            .replace("→", "->")
            .replace("←", "<-")
            .replace("⇒", "=>")
            .replace("•", chr(183))
            .replace("…", "...")
            .replace("‘", "'")
            .replace("’", "'")
            .replace("“", '"')
            .replace("”", '"')
            .replace("·", "-")
            .replace("✓", "v")
            .replace("✕", "x")
            .replace("✗", "x")
            .replace("×", "x")
            .replace("≈", "~")
            .replace("≤", "<=")
            .replace("≥", ">=")
    )


def main():
    pdf = PDF()

    # ── Cover ──────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.set_fill_color(*BG_CREAM)
    pdf.rect(0, 0, pdf.w, pdf.h, style="F")

    logo = DESIGN / "Logo.png"
    if logo.exists():
        pdf.image(str(logo), x=(pdf.w - 50) / 2, y=40, w=50)

    pdf.set_y(100)
    pdf.set_font("Helvetica", "B", 36)
    pdf.set_text_color(*BROWN_DARK)
    pdf.cell(0, 16, "ASL Bridge", ln=1, align="C")

    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(*BROWN_MID)
    pdf.cell(0, 8, safe("Real-time ASL <-> English communication"), ln=1, align="C")
    pdf.ln(2)
    pdf.set_font("Helvetica", "I", 12)
    pdf.set_text_color(*MUTED)
    pdf.cell(0, 7, safe('"No special request. No interpreter. No aid. Just talk."'),
             ln=1, align="C")

    pdf.ln(40)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*BROWN_DARK)
    pdf.cell(0, 7, "Project Overview", ln=1, align="C")
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*INK)
    pdf.cell(0, 6, "Hackathon Submission - ConHacks 2026", ln=1, align="C")

    pdf.set_y(-50)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*MUTED)
    pdf.cell(0, 5, "Team: Kai - Bob - Max - Dave", ln=1, align="C")
    pdf.cell(0, 5, "36-hour hackathon - April 2026", ln=1, align="C")
    pdf.cell(0, 5, "github.com/naik26m3/signly-conhacks-2026", ln=1, align="C")

    # ── Page 2: Table of Contents ──────────────────────────────────────────
    pdf.add_page()
    pdf.h1("Table of Contents")
    toc = [
        ("1. Executive Summary", "3"),
        ("2. The Problem We Set Out to Solve", "3"),
        ("3. Our Solution: Three Conversational Modes", "4"),
        ("4. End-to-End System Architecture", "6"),
        ("5. Technology Stack", "7"),
        ("6. Backend Deep Dive (FastAPI + ARQ)", "8"),
        ("7. Computer Vision: Hand and Face Tracking", "10"),
        ("8. AI Inference: Gemini Prompt Engineering", "11"),
        ("9. Speech & Voice Design: ElevenLabs", "12"),
        ("10. Frontend: Expo React Native App", "13"),
        ("11. Data, Storage and Conversation State", "15"),
        ("12. Observability and Reliability", "16"),
        ("13. Latency Engineering: Hitting the 2-Second Bar", "16"),
        ("14. Roadmap and Post-Hackathon Plans", "17"),
        ("15. Team, Credits and Closing Notes", "18"),
    ]
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*INK)
    for title, page in toc:
        # title ............... page
        x = pdf.get_x()
        y = pdf.get_y()
        pdf.cell(0, 7, title, ln=0)
        pdf.set_x(pdf.w - pdf.r_margin - 12)
        pdf.cell(12, 7, page, ln=1, align="R")
        pdf.set_draw_color(*RULE)
        pdf.set_line_width(0.15)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
        pdf.ln(1)

    pdf.ln(5)
    pdf.callout(
        "About this document",
        safe("This overview describes ASL Bridge as built during ConHacks 2026 - "
             "the architecture, the engineering decisions, the trade-offs we accepted "
             "in 36 hours, and where the project goes next. Code references throughout "
             "point to actual files in the repository."),
    )

    # ── Page 3: Sections 1 + 2 ────────────────────────────────────────────
    pdf.add_page()
    pdf.h1("1. Executive Summary")
    pdf.body(safe(
        "ASL Bridge is a mobile application that lets a Deaf person and a hearing person "
        "hold a face-to-face conversation in real time without an interpreter. The Deaf user "
        "signs naturally; the app recognises the sign, speaks the English translation aloud, "
        "and stores it in the chat thread. The hearing user replies with their voice; the app "
        "transcribes it, converts the transcript to ASL gloss, and (optionally) renders an "
        "animated avatar performing the ASL response."
    ))
    pdf.body(safe(
        "Everything is built around one simple bar: end-to-end latency under two seconds. "
        "The whole pipeline - video capture, MediaPipe hand tracking, Gemini vision inference, "
        "ElevenLabs text-to-speech, persistence to PostgreSQL, and audio playback on the phone - "
        "is engineered to fit inside that budget."
    ))
    pdf.body(safe(
        "The system is shipped as a containerised stack (FastAPI API + ARQ worker + Postgres + "
        "Redis + SeaweedFS + Prometheus/Grafana/Loki) and an Expo React Native client. The app "
        "exposes three modes: sign-to-speech translation, hearing-to-deaf avatar animation, and "
        "AI voice design. It uses Gemini 2.5 Flash for sign recognition and voice persona "
        "generation, MediaPipe HandLandmarker (VIDEO mode) for 21-point hand tracking, "
        "MediaPipe FaceLandmarker for spatial anchor points, and ElevenLabs Scribe for "
        "speech-to-text, Multilingual v2 for text-to-speech, and Voice Design API for "
        "custom AI-generated voices. Animation of the hearing-to-deaf path is handled by "
        "an embedded sign.mt avatar viewer."
    ))

    pdf.h1("2. The Problem We Set Out to Solve")
    pdf.body(safe(
        "An estimated 70 million people worldwide use a sign language as their first language. "
        "Despite that, every day they bump into hearing people who cannot sign - at the doctor, "
        "in customer service, at school, on the bus. Today's options are professional human "
        "interpreters (excellent but scarce, expensive, and requiring scheduling), pen-and-paper, "
        "or hand-typed messages on a phone. None of them feel like a real conversation."
    ))
    pdf.h3("What is broken about the existing options")
    pdf.bullets([
        safe("Interpreters need to be booked - useless for spontaneous interactions."),
        safe("Typing on a phone breaks eye contact, slows the exchange, and erases the visual "
             "richness of sign language."),
        safe("Existing translation apps mostly do one direction (sign-to-text) and demand "
             "studio-clean conditions, perfectly framed hands, and a small fixed vocabulary."),
        safe("None of them close the loop on the hearing person's side - the Deaf user "
             "still has to read text, which is slower and less natural than receiving signs."),
    ])
    pdf.h3("Our north star")
    pdf.callout(
        "Design principle",
        safe("If the conversation feels noticeably slower than two people both speaking English, "
             "we have failed. Latency, eye contact, and visual feedback matter more than "
             "vocabulary breadth at this stage."),
    )

    # ── Page 4-5: Section 3 ────────────────────────────────────────────────
    pdf.add_page()
    pdf.h1("3. Our Solution: Three Conversational Modes")
    pdf.body(safe(
        "The app exposes three screens, each managing its own conversation history via a "
        "shared SessionContext. All three tabs share the same session ID so a voice persona "
        "designed on the Voice tab can be selected for read-aloud on either conversation tab."
    ))

    pdf.h2("Translate (default tab)")
    pdf.body(safe(
        "A chat-style interface with two large action buttons at the bottom: a camera FAB "
        "(brown) and a microphone FAB (dark brown, red while recording). Tapping the camera "
        "opens a full-screen recorder; tapping the mic starts a voice recording. As soon as "
        "the result returns, a chat bubble slides up with the gloss, the natural English "
        "translation, and a speaker icon to replay the audio."
    ))
    pdf.bullets([
        safe("Sign bubbles render on the LEFT, brown outline, with the ASL gloss as the bold "
             "primary line and the natural English translation underneath."),
        safe("Speech bubbles render on the RIGHT, solid brown, with the transcript as primary "
             "and the back-translated ASL gloss as secondary."),
        safe("While a sign clip is being processed we show a 'pending bubble' with a "
             "rotating set of Giphy meme GIFs - SpongeBob waiting, Skeleton 'where you at?', "
             "Titanic '84 years' - so the wait feels human, not stuck."),
        safe("On a successful sign result the app auto-plays the ElevenLabs TTS audio so the "
             "hearing person hears the translation immediately, without anyone tapping anything."),
        safe("A voice-reasoning chip shows the selected voice's tone, pace, and rationale. "
             "A history drawer (slide-in from left) shows conversation history with timestamps "
             "and a voice picker shortcut."),
    ])

    pdf.h2("Animation (second tab)")
    pdf.body(safe(
        "The Animation page is the hearing-to-deaf complement. The hearing person types a "
        "message or taps the mic, and an embedded WebView shows an avatar performing the ASL "
        "translation. We use sign.mt as the avatar engine, but inject a CSS overlay at page "
        "load to hide their language picker, input bar, and FAB controls so only the avatar "
        "viewer is visible - our native Expo input drives the URL state."
    ))
    pdf.code(safe(
        "// AnimationPage.jsx (excerpt)\n"
        "function buildSignMtUrl(text) {\n"
        "  const params = new URLSearchParams({ spl: 'en', sil: 'ase', text });\n"
        "  return `${SIGN_MT_BASE}?${params.toString()}`;\n"
        "}\n"
        "<WebView injectedJavaScriptBeforeContentLoaded={HIDE_CHROME_JS}\n"
        "         injectedJavaScript={HIDE_CHROME_JS} ... />"
    ))
    pdf.body(safe(
        "Because Angular hydrates after first paint, the injected script also installs a "
        "MutationObserver that re-applies the hide-chrome CSS whenever the DOM changes - "
        "without it, the sign.mt UI flickers back in after a few hundred milliseconds."
    ))
    pdf.callout(
        "Why a WebView?",
        safe("Building a full SignLM avatar pipeline was out of scope for 36 hours. sign.mt has "
             "a public, well-tested avatar viewer that already supports ASL gloss output, so we "
             "treat it as Phase-1 plumbing and plan to swap in our own avatar in Phase 2."),
    )

    pdf.h2("Voice Design (third tab)")
    pdf.body(safe(
        "The Voice page is a conversation UI for creating custom AI voices. The user describes "
        "the voice they want in plain English ('a calm, slow, warm older woman with a slight "
        "Southern accent'). Gemini generates a structured voice persona; ElevenLabs Voice "
        "Design API synthesises a sample clip. The created voice appears as a VoiceBubble with "
        "tags, description, sample text, and a play button."
    ))
    pdf.bullets([
        safe("UserBubble (right): the user's description prompt."),
        safe("PendingBubble (left): a multi-phase animation cycling through "
             "'Gemini designing...' -> 'ElevenLabs generating...' while both API calls run."),
        safe("VoiceBubble (left): the finished voice card with a speaker tag list, "
             "description blurb, and playable audio sample."),
        safe("Created voices are stored in SessionContext and appear in the voice picker "
             "under 'My Voices' on any tab, so the same persona can read aloud sign "
             "translations or animation captions."),
    ])
    pdf.code(safe(
        "// Voice flow\n"
        "POST /api/v1/voice/design  { description }  -> { voice_id, name, preview_url }\n"
        "POST /api/v1/voice/speak   { voice_id, text } -> mp3 audio stream"
    ))

    # ── Page 5: Section 4 - Architecture ──────────────────────────────────
    pdf.add_page()
    pdf.h1("4. End-to-End System Architecture")
    pdf.body(safe(
        "The system splits into three planes: the mobile client, a synchronous FastAPI surface "
        "for fast metadata operations, and an asynchronous ARQ worker pool for everything that "
        "involves an ML model or third-party API call. Splitting these cleanly is what makes the "
        "perceived latency low: the client gets a 202 Accepted in under 100ms while the heavy "
        "work runs in parallel and is delivered via a Redis-backed result key."
    ))

    pdf.h2("Path 1 - Deaf to Hearing")
    pdf.code(safe(
        "Front camera (Expo CameraView, 480p H.264, max 10s)\n"
        "  -> POST /api/v1/sign/recognize  (multipart/form-data)\n"
        "     . API writes file to shared tmp volume\n"
        "     . API enqueues ARQ job with shared_tmp_path\n"
        "     . API returns { video_id, status: 'processing' }\n"
        "  -> Worker:\n"
        "     1. ffmpeg -> 480p H.264 (smaller payload, faster Gemini upload)\n"
        "     2. MediaPipe HandLandmarker (VIDEO) -> 21-pt hand sequence\n"
        "     3. MediaPipe FaceLandmarker -> facial anchor points\n"
        "     4. Gemini 2.5 Flash recognises the sign using video + landmarks\n"
        "     5. ElevenLabs TTS synthesises the English audio\n"
        "     6. Result + audio_url written to Redis (sign:{video_id})\n"
        "     7. Conversation + Message rows persisted to Postgres\n"
        "  -> Client polls /api/v1/sign/result/{id} -> auto-plays audio"
    ))

    pdf.h2("Path 2 - Hearing to Deaf")
    pdf.code(safe(
        "Mic (Expo Audio.Recording, m4a)\n"
        "  -> POST /api/v1/speech/transcribe (synchronous, no worker)\n"
        "     . ElevenLabs Scribe transcribes audio -> English text\n"
        "     . hearing_to_deaf message persisted to Postgres\n"
        "     . Returns { transcript }\n"
        "  -> POST /api/v1/speech/gloss { text }\n"
        "     . Gemini Flash returns ASL gloss notation\n"
        "  -> Animation tab: WebView opens sign.mt with text=<transcript>\n"
        "     . Avatar performs the sign in-app"
    ))

    pdf.h2("Why split sync vs async this way?")
    pdf.bullets([
        safe("Sign recognition is the slowest hop (1.5-2.0s) because it bundles ffmpeg, "
             "MediaPipe and a Gemini round-trip. Putting it on a worker lets the API return "
             "in ~50ms and unblocks the UI."),
        safe("Speech transcription is fast enough (300-700ms) that an extra polling round "
             "would actually hurt UX, so it stays inline."),
        safe("Both paths share a single Conversation row keyed by X-Session-ID, so the chat "
             "history endpoint returns a unified, ordered thread."),
    ])

    # ── Page 6: Section 5 - Tech Stack ────────────────────────────────────
    pdf.add_page()
    pdf.h1("5. Technology Stack")
    pdf.h2("Mobile client")
    pdf.kv_table([
        ("Runtime", "Expo SDK 54, React Native 0.81, React 19"),
        ("Camera", "expo-camera 17 (CameraView, video mode, front + back facing)"),
        ("Audio", "expo-av 16 (Audio.Recording HIGH_QUALITY preset, Audio.Sound playback)"),
        ("Video preview", "expo-video 3 (useVideoPlayer + VideoView)"),
        ("Animation", "react-native-reanimated 4, native Animated API for bubbles"),
        ("Avatar", "react-native-webview 13 hosting sign.mt with chrome stripped"),
        ("System TTS", "expo-speech (device OS voices, grouped by language in voice picker)"),
        ("State", "React Context (SessionContext) - per-tab history + created voices"),
        ("Routing", "Three-tab manual switch in app/index.tsx (Translate / Animation / Voice)"),
    ])

    pdf.h2("Backend")
    pdf.kv_table([
        ("API", "FastAPI 0.115 + Uvicorn 0.30 (Python 3.11)"),
        ("Worker", "ARQ 0.25 (Redis-backed async task queue, max_jobs=2, timeout=120s)"),
        ("Database", "PostgreSQL 16 + asyncpg 0.31 + SQLAlchemy 2.0 (async) + Alembic"),
        ("Cache / queue", "Redis 7"),
        ("Object store", "SeaweedFS (master + volume + filer)"),
        ("Computer vision", "MediaPipe 0.10.35 (HandLandmarker + FaceLandmarker)"),
        ("Vision LLM", "Gemini 2.5 Flash + 2.5 Flash-Lite fallback (google-genai 1.74)"),
        ("STT / TTS", "ElevenLabs Scribe v1 + Multilingual v2"),
        ("Observability", "Prometheus, Loki + Promtail, Grafana, Langfuse LLM tracing"),
        ("Container", "Docker Compose: api, worker, postgres, redis, 3x seaweedfs, monitoring"),
    ])

    pdf.h2("Why these choices?")
    pdf.bullets([
        safe("Expo over bare React Native: needed to be running on the judges' phones in five "
             "minutes, with no Xcode/Android Studio dance."),
        safe("FastAPI: type hints + Pydantic + automatic OpenAPI at /docs gave the frontend a "
             "typed contract before the API existed."),
        safe("ARQ over Celery: lighter, async-native, Redis-only - no broker, no thread-pool "
             "gymnastics, shares the API's async ecosystem."),
        safe("MediaPipe over a custom CNN: zero training time, 21-point output is exactly the "
             "abstraction Gemini understands as JSON."),
        safe("Gemini 2.5 Flash: the only frontier vision model with latency low enough on "
             "short clips to fit our 2s bar in one round-trip."),
    ])

    # ── Page 7-8: Section 6 - Backend Deep Dive ───────────────────────────
    pdf.add_page()
    pdf.h1("6. Backend Deep Dive (FastAPI + ARQ)")
    pdf.body(safe(
        "The backend is laid out as a conventional FastAPI app with explicit modules per "
        "concern. The module map follows the principle that each file owns exactly one "
        "external dependency or one type of artefact:"
    ))
    pdf.code(safe(
        "backend/\n"
        "  main.py                  # app factory, lifespan, router wiring\n"
        "  server.py                # uvicorn entrypoint\n"
        "  worker.py                # ARQ worker (sign recognition + TTS + DB)\n"
        "  config/\n"
        "    settings.py            # Pydantic Settings (loads .env)\n"
        "    database.py            # async SQLAlchemy engine + Session\n"
        "    redis.py               # Redis pool\n"
        "    gemini.py              # google-genai client factory\n"
        "    elevenlabs.py          # ElevenLabs client factory\n"
        "    langfuse.py            # Langfuse observability client\n"
        "  db/models.py             # SQLAlchemy: Conversation + Message\n"
        "  routers/\n"
        "    health.py  sign.py  speech.py  uploads.py  conversations.py  voice.py\n"
        "  schemas/                 # Pydantic request/response models (incl. voice.py)\n"
        "  services/\n"
        "    storage.py             # SeaweedFS save/validate (save_bytes)\n"
        "    inference.py           # Gemini: recognize_sign, gloss <-> english, voice design\n"
        "    speech.py              # ElevenLabs: STT + TTS + voice design\n"
        "    conversation.py        # DB helpers (upsert + insert)\n"
        "    collector.py           # JSONL data-collection logging\n"
        "  middleware/request_logger.py\n"
        "  migrations/              # Alembic"
    ))

    pdf.h2("Lifespan: services live on app.state")
    pdf.body(safe(
        "FastAPI's lifespan context manager wires up the heavy clients exactly once at startup "
        "and tears them down on shutdown. This is critical for two reasons: (1) the MediaPipe "
        "HandLandmarker takes ~400ms to load and we cannot afford to do it per request; "
        "(2) Gemini and ElevenLabs clients hold pooled HTTP connections."
    ))
    pdf.code(safe(
        "@asynccontextmanager\n"
        "async def lifespan(app: FastAPI):\n"
        "    await Database.connect()\n"
        "    await RedisClient.connect()\n"
        "    HandTracker.load()\n"
        "    FaceTracker.load()\n"
        "    gemini = GeminiClient.connect()\n"
        "    elevenlabs = ElevenLabsClient.connect()\n"
        "    app.state.inference = InferenceService(gemini=gemini, langfuse=langfuse)\n"
        "    app.state.speech = SpeechService(elevenlabs=elevenlabs)\n"
        "    yield\n"
        "    HandTracker.unload(); FaceTracker.unload()\n"
        "    await Database.disconnect(); await RedisClient.disconnect()"
    ))

    pdf.h2("Endpoints")
    pdf.kv_table([
        ("GET  /api/v1/health", "Service status + API key availability"),
        ("POST /api/v1/sign/recognize", "Multipart video; returns 202 + video_id"),
        ("POST /api/v1/sign/detect-hands", "Pre-flight MediaPipe check before recognise"),
        ("GET  /api/v1/sign/result/{video_id}", "Poll Redis for the worker's output"),
        ("GET  /api/v1/sign/audio/{video_id}", "Proxy TTS audio out of SeaweedFS"),
        ("POST /api/v1/sign/corrections", "Append a human-corrected gloss"),
        ("POST /api/v1/speech/transcribe", "Audio -> ElevenLabs Scribe -> transcript"),
        ("POST /api/v1/speech/gloss", "JSON { text } -> Gemini -> ASL gloss"),
        ("GET  /api/v1/conversations/{session_id}/messages", "Full ordered chat thread"),
        ("GET  /api/v1/conversations/{session_id}/title", "Auto-generated 1-3 word title"),
        ("POST /api/v1/voice/design", "Text description -> Gemini persona -> ElevenLabs voice"),
        ("POST /api/v1/voice/speak", "Synthesise speech with a created custom voice"),
    ])

    pdf.h2("Worker pipeline (worker.py: process_sign_video)")
    pdf.body(safe(
        "The ARQ worker function is the most complex single piece of code in the project. Its "
        "shape is deliberate: every step has a fail-soft fallback so we never block the user's "
        "result on a non-critical hop (TTS, DB persistence, observability). The worker runs in "
        "its own container, on its own Redis queue, with max_jobs=2 to avoid GPU/CPU contention."
    ))
    pdf.code(safe(
        "1. Receive (video_id, content_type, session_id, shared_tmp_path)\n"
        "2. Fast path: if shared_tmp_path exists -> use it (skip SeaweedFS download)\n"
        "   Fallback: GET <filer>/videos/{id}.mp4 into a NamedTemporaryFile\n"
        "3. ffmpeg -> 480p H.264 mp4 (libx264 crf=28 ultrafast, +faststart, AAC 64k)\n"
        "4. HandTracker.process_video(...) -> landmark_sequence, landmarks_found\n"
        "   - face landmarks every 4th frame, hand landmarks every 2nd frame\n"
        "   - per-frame wrist velocity (dx, dy) for motion disambiguation\n"
        "5. inference.recognize_sign(video, landmarks) -> { gloss, english, confidence }\n"
        "   - inline base64 if <19MB, Files API otherwise\n"
        "   - thinking_budget=0, automatic_function_calling disabled\n"
        "6. ElevenLabs.text_to_speech.convert(...) -> mp3 bytes\n"
        "7. save_bytes(audio, video_id, folder='audio', ext='mp3') -> SeaweedFS\n"
        "8. upsert_conversation(session_id) + insert_message(deaf_to_hearing)\n"
        "9. collector.log_inference -> data/raw/inferences.jsonl (silent training set)\n"
        "10. redis.setex('sign:{video_id}', 3600, json) -> client polls and gets result"
    ))

    pdf.h2("Fast-path optimisation: shared tmp volume")
    pdf.body(safe(
        "The naive worker design uploads the video to SeaweedFS in the API, then has the worker "
        "download it back. That double-hop costs ~150-300ms on a 4-8MB clip. We bypassed it by "
        "writing to a shared docker volume (/app/tmp_videos) directly inside the API handler "
        "and passing the path through to the worker as the shared_tmp_path argument. SeaweedFS "
        "still gets the bytes - in a BackgroundTask that runs concurrently - so the artefact is "
        "durable for replay, but the worker doesn't wait for it."
    ))
    pdf.callout(
        "Why is this safe?",
        safe("Both api and worker mount the same backend/ tree, so /app/tmp_videos is a real "
             "shared filesystem. The worker unlinks the file at the end. In the worst case "
             "(worker crash before unlink), the file is reaped by docker volume rotation."),
    )

    # ── Page 9: Section 7 - Computer Vision ───────────────────────────────
    pdf.add_page()
    pdf.h1("7. Computer Vision: Hand and Face Tracking")
    pdf.body(safe(
        "models/handTracking.py wraps two MediaPipe Tasks landmarkers as singleton classes - "
        "HandTracker and FaceTracker. Both load lazily at backend startup and unload on shutdown. "
        "We expose three operations: a quick image-mode hand detect for the pre-flight UX, a "
        "video-mode landmark sequence for the inference pipeline, and a face-tracker that emits "
        "exactly nine named anchor points relevant to ASL placement."
    ))

    pdf.h2("Quick pre-flight: HandTracker.quick_detect")
    pdf.body(safe(
        "Before sending the video to Gemini, the camera-recorder posts the just-recorded clip "
        "to /api/v1/sign/detect-hands. The endpoint samples 6 evenly-spaced frames in IMAGE "
        "mode and returns true as soon as ONE of them contains a hand. On a 10-second clip this "
        "takes ~600ms and means a re-take prompt costs a tiny fraction of an inference call."
    ))
    pdf.code(safe(
        "// camera-recorder.tsx (excerpt)\n"
        "const [handsCheck, setHandsCheck] = useState<HandsCheck>('idle');\n"
        "useEffect(() => {\n"
        "  if (!previewUri) return;\n"
        "  setHandsCheck('checking');\n"
        "  detectHands(previewUri).then(r =>\n"
        "    setHandsCheck(r.data.hands_detected ? 'detected' : 'missing'));\n"
        "}, [previewUri]);"
    ))

    pdf.h2("Video-mode landmarks: HandTracker.process_video")
    pdf.body(safe(
        "The full inference pass runs in VIDEO mode (which preserves temporal smoothing across "
        "frames), num_hands=2, and emits a JSON-friendly sequence. Each entry includes:"
    ))
    pdf.bullets([
        safe("frame index"),
        safe("right and left hand landmarks - 21 [x, y, z] tuples each, normalised 0-1, "
             "rounded to 4 decimal places to keep the JSON small"),
        safe("face: nine named landmarks - forehead, chin, nose_tip, left_cheek, right_cheek, "
             "mouth_left, mouth_right, left_eyebrow, right_eyebrow - sampled every 4th frame "
             "and carried forward (faces barely move, so 7-8 fps saves 2-3s of MediaPipe time)"),
        safe("right_vel and left_vel: wrist deltas since previous sample. These are critical "
             "for motion disambiguation - distinguishing 9 from 19, COME from GO, HELLO from "
             "MY by the magnitude of wrist movement"),
    ])
    pdf.h2("Why both face and hand?")
    pdf.callout(
        "Sign linguistics 101",
        safe("ASL is not just hands. The same handshape at the forehead vs at the chin is a "
             "different sign. Velocity magnitude separates fingerspelling (static) from numbers "
             "with motion modifiers. By including face anchor points and wrist velocity in the "
             "Gemini prompt, we get a model that can reason geometrically about WHERE the hand "
             "is, not just what shape it makes."),
    )

    # ── Page 10: Section 8 - AI Inference / Prompting ────────────────────
    pdf.add_page()
    pdf.h1("8. AI Inference: Gemini Prompt Engineering")
    pdf.body(safe(
        "services/inference.py is where the 'think hard' happens. We use Gemini 2.5 Flash as "
        "the primary model with 2.5 Flash-Lite as a retry fallback. On a clean inline path the "
        "round-trip is consistently 800-1200ms; on the Files API path it adds 2-4s to wait for "
        "the file to become ACTIVE."
    ))

    pdf.h2("Closed-set classification with a vocabulary prior")
    pdf.body(safe(
        "Hackathon constraints forced a key decision: do we try to recognise the full ASL "
        "lexicon (impossible reliably in 36h) or a small demo-friendly vocabulary (reliable, "
        "demoable, useful for the judge interaction)? We chose the latter. The recognition "
        "prompt explicitly enumerates five demo phrases and instructs Gemini to pick exactly "
        "one - never UNKNOWN."
    ))
    pdf.code(safe(
        "1. HI WHAT YOUR NAME       -> 'Hi, what is your name?'\n"
        "2. MY NAME K-A-I.          -> 'My name is Kai.'\n"
        "3. HOW YOU.                -> 'How are you?'\n"
        "4. PHO                     -> 'Pho.'\n"
        "5. NICE MEET YOU           -> 'Nice to meet you.'"
    ))

    pdf.h2("Anti-bias rule")
    pdf.body(safe(
        "Early prompts had Gemini gravitate toward fingerspelled phrases whenever it saw any "
        "letter-like handshape. We patched this with an explicit anti-bias clause that requires "
        "THREE separate letter handshapes in quick succession before classifying as a "
        "fingerspelled phrase, plus disambiguation rules for the most-confused pairs (HI vs MY, "
        "HOW vs YOU, NICE vs MEET, NAME alone is not enough to imply phrase 2 because phrase 1 "
        "also contains NAME)."
    ))

    pdf.h2("Inline vs Files API")
    pdf.body(safe(
        "Files API is only worth using for videos > 19MB - most sign clips after 480p transcode "
        "are 1-4MB, so we embed the bytes directly via types.Blob. This skips the 'wait for "
        "ACTIVE' polling loop and shaves 2-4 seconds off the worst case. Above 19MB we fall "
        "back to Files API and poll for ACTIVE up to 30 seconds."
    ))

    pdf.h2("Latency knobs")
    pdf.bullets([
        safe("thinking_budget=0 - disables Gemini's chain-of-thought entirely. Costs us a "
             "small amount of accuracy on borderline samples, but cuts ~600-1200ms per call."),
        safe("automatic_function_calling.disable=True - avoids an internal SDK loop that "
             "occasionally hangs the request for 60-90s on otherwise short queries."),
        safe("3.0 fps video sampling (Gemini's default is 1 fps) - captures sub-second motion "
             "modifiers like the WHERE-shake and the teen-number wrist twist."),
        safe("Three-step retry: Flash@0s, Flash@0.5s, Flash-Lite@1.0s - covers transient 500s "
             "from Gemini without doubling the latency on the first try."),
        safe("Hard 30s asyncio.wait_for - guarantees the worker never holds the queue slot "
             "indefinitely. On timeout we return TIMEOUT to Redis and the user sees 'retry'."),
    ])

    # ── Page 11: Section 9 - Speech + Voice Design ────────────────────────
    pdf.add_page()
    pdf.h1("9. Speech & Voice Design: ElevenLabs")
    pdf.body(safe(
        "services/speech.py is the smallest service in the backend, and intentionally so: "
        "ElevenLabs is the bottleneck for both audio in and audio out, and our job is to feed "
        "it cleanly and not block on it. The class wraps both directions because they share "
        "the same client and connection pool."
    ))

    pdf.h2("Speech-to-text: Scribe v1")
    pdf.body(safe(
        "The frontend records audio with expo-av's HIGH_QUALITY preset (m4a, AAC, 44.1kHz). The "
        "API forwards the file as a BytesIO into ElevenLabs' speech_to_text.convert with "
        "model_id=scribe_v1, language_code=en, tag_audio_events=False. We then strip "
        "parenthetical noise tags like '(audience laughing)' that occasionally slip through and "
        "collapse runs of whitespace."
    ))
    pdf.code(safe(
        "_NOISE_RE = re.compile(r'[\\(\\[\\<][^\\)\\]\\>]{1,60}[\\)\\]\\>]')\n"
        "raw = result.text\n"
        "text = re.sub(r'\\s+', ' ', _NOISE_RE.sub('', raw)).strip()"
    ))

    pdf.h2("Text-to-speech: Multilingual v2")
    pdf.body(safe(
        "TTS uses model_id=eleven_multilingual_v2 and voice Rachel (the widely-available "
        "default voice id 21m00Tcm4TlvDq8ikWAM, configurable via ELEVENLABS_VOICE_ID). The "
        "convert() call streams chunks; we join them in a thread (asyncio.to_thread) and write "
        "the resulting mp3 bytes to SeaweedFS at /audio/{video_id}.mp3."
    ))

    pdf.h2("Audio playback on the client")
    pdf.body(safe(
        "Once the polling loop sees status='done' with a truthy audio_url, the React Native "
        "client builds the URL via getAudioUrl(videoId), creates an Audio.Sound, calls "
        "playAsync, and registers a callback that unloads the sound on didJustFinish. We also "
        "expose a speaker icon on the bubble so the user can replay any past message."
    ))
    pdf.code(safe(
        "// TranslatePage.jsx (excerpt)\n"
        "const playAudio = useCallback(async (videoId) => {\n"
        "  const { sound } = await Audio.Sound.createAsync({ uri: getAudioUrl(videoId) });\n"
        "  await sound.playAsync();\n"
        "  sound.setOnPlaybackStatusUpdate(s => {\n"
        "    if (s.didJustFinish) sound.unloadAsync();\n"
        "  });\n"
        "}, []);"
    ))

    pdf.callout(
        "Failure mode that does not block the user",
        safe("If TTS or audio upload fails, the worker still writes the recognition result to "
             "Redis with audio_url: null. The user gets the gloss + English text immediately "
             "and the speaker icon is hidden. We treat audio as a non-critical enhancement."),
    )

    pdf.h2("Voice Design: custom AI voices")
    pdf.body(safe(
        "The Voice Design feature lets users create a reusable voice persona through a "
        "two-step AI pipeline. The user types a natural language description; Gemini 2.5 Flash "
        "generates structured voice parameters (gender, age, accent, tone, pace); ElevenLabs "
        "Voice Design API instantiates the voice and returns a preview clip. The backend "
        "exposes two endpoints:"
    ))
    pdf.bullets([
        safe("POST /api/v1/voice/design - accepts { description } and returns "
             "{ voice_id, name, labels, preview_url }. The Gemini call converts free-form text "
             "into ElevenLabs VoiceDesign parameters before the ElevenLabs call."),
        safe("POST /api/v1/voice/speak - accepts { voice_id, text } and streams mp3 audio "
             "synthesised with the custom voice. Used for the 'Read aloud' action on any "
             "message bubble when a custom voice is selected."),
    ])
    pdf.body(safe(
        "On the frontend, created voices are stored in SessionContext.createdVoices and "
        "surfaced in the VoicePickerModal under a 'My Voices' section alongside system OS "
        "voices grouped by language. Selecting a voice applies it to all 'Read aloud' actions "
        "across all tabs for the current session."
    ))

    # ── Page 13: Section 10 - Frontend ────────────────────────────────────
    pdf.add_page()
    pdf.h1("10. Frontend: Expo React Native App")
    pdf.body(safe(
        "The Expo client now has three top-level pages with shared state managed through "
        "SessionContext. Two custom hooks (useVideoUpload + useSpeechUpload) wrap the upload "
        "state machines, and a typed API client lives in lib/api.ts. SessionContext holds "
        "per-tab conversation history, the selected voice, and the created-voices list - "
        "the only cross-tab state that needs to survive tab switches."
    ))

    pdf.h2("Module layout")
    pdf.code(safe(
        "frontend/\n"
        "  app/\n"
        "    _layout.tsx            # root navigation shell\n"
        "    index.tsx              # three-tab switcher (Translate/Animation/Voice)\n"
        "    TranslatePage.jsx      # chat UI, sign + speech, history drawer\n"
        "    AnimationPage.jsx      # sign.mt WebView + chat input + voice picker\n"
        "    VoicePage.jsx          # voice design chat (describe -> create -> preview)\n"
        "  components/\n"
        "    camera-recorder.tsx    # CameraView + record + preflight detectHands\n"
        "    video-preview.tsx      # VideoView + upload result panel\n"
        "    history-drawer.tsx     # slide-in left panel (300px): conversation list\n"
        "    voice-picker-modal.tsx # system voices by language + My Voices section\n"
        "  contexts/\n"
        "    SessionContext.tsx     # per-tab history, selectedVoice, createdVoices\n"
        "  hooks/\n"
        "    use-video-upload.ts    # POST /sign/recognize + poll /result\n"
        "    use-speech-upload.ts   # record + POST /speech/transcribe + /gloss\n"
        "  lib/\n"
        "    api.ts                 # typed request() + endpoint helpers"
    ))

    pdf.h2("SessionContext")
    pdf.body(safe(
        "SessionContext is a React Context that wraps the entire app (provided in _layout.tsx). "
        "It tracks three independent conversation histories - one per tab - so switching tabs "
        "never loses messages. It also holds the currently selected voice (system or custom) and "
        "the list of voices the user has created on the Voice tab. Conversation titles are "
        "auto-derived from the first message locally and confirmed via the backend title endpoint "
        "after the third message."
    ))

    pdf.h2("Camera recorder UX")
    pdf.body(safe(
        "The CameraRecorder component is responsible for everything between the user opening "
        "the camera and the worker receiving the file. It shows a live countdown badge "
        "(MAX_RECORD_SECONDS=10), a flash toggle (back camera only), a flip button, and a stop "
        "button. After recording it transitions to a preview view with a 'hands detected' "
        "badge whose colour reflects the pre-flight result."
    ))
    pdf.bullets([
        safe("Front camera default - it is the natural framing for self-recording while "
             "talking to someone in front of you."),
        safe("Camera-ready promise: handleRecord awaits a 'camera ready' resolver before "
             "calling recordAsync to prevent the rare 'camera not initialised' iOS crash."),
        safe("MAX_RECORD_SECONDS=10 ceiling - keeps payloads small, pushes the user toward "
             "isolated, demoable signs, and bounds the inference cost."),
        safe("Hands badge colours: green (detected), amber (missing - retake?), red (check "
             "failed). The user can still proceed if they choose."),
    ])

    pdf.h2("History drawer & voice picker")
    pdf.body(safe(
        "history-drawer.tsx slides in from the left (width 300px) and shows the current tab's "
        "conversation list with relative timestamps and a 'New' button. A voice-picker shortcut "
        "at the bottom opens the VoicePickerModal. voice-picker-modal.tsx groups system OS "
        "voices (via expo-speech) by language and shows a 'My Voices' section at the top for "
        "any AI-generated voices from the Voice tab. A preview button speaks a sample sentence "
        "in the selected voice before committing."
    ))

    pdf.h2("Speech upload hook & animation chrome injection")
    pdf.body(safe(
        "useSpeechUpload returns { isRecording, isProcessing, start, stop }. start() requests "
        "permissions, calls Audio.setAudioModeAsync, and creates a HIGH_QUALITY recording. "
        "stop() unloads the recording, posts the m4a to /speech/transcribe, then posts the "
        "transcript to /speech/gloss to enrich the message bubble with both the spoken "
        "sentence AND its ASL gloss back-translation. The AnimationPage's WebView injects two "
        "scripts (before and after Angular hydration) that insert a hide-chrome style tag and "
        "a MutationObserver so sign.mt's own UI never becomes visible."
    ))

    # ── Page 15: Section 11 - Data + Storage ──────────────────────────────
    pdf.add_page()
    pdf.h1("11. Data, Storage and Conversation State")
    pdf.h2("Postgres schema (db/models.py)")
    pdf.body(safe(
        "Two tables - one Conversation per session, many Messages per conversation. The Message "
        "row carries direction, content, gloss, audio_url and confidence. user_id is nullable "
        "so the schema is auth-ready without requiring auth on day 1."
    ))
    pdf.code(safe(
        "class Conversation(Base):\n"
        "    id: UUID PK = uuid4()\n"
        "    session_id: UUID UNIQUE NOT NULL\n"
        "    user_id: UUID NULL                      # ready for auth\n"
        "    created_at: TIMESTAMPTZ NOT NULL\n"
        "\n"
        "class Message(Base):\n"
        "    id: UUID PK = uuid4()\n"
        "    conversation_id: UUID FK -> conversations.id ON DELETE CASCADE\n"
        "    direction: VARCHAR(32)   # 'deaf_to_hearing' | 'hearing_to_deaf'\n"
        "    content: TEXT             # natural language string\n"
        "    gloss: TEXT NULL          # ASL gloss\n"
        "    audio_url: TEXT NULL      # SeaweedFS mp3 URL\n"
        "    confidence: FLOAT NULL    # only set for sign recognition\n"
        "    created_at: TIMESTAMPTZ NOT NULL"
    ))

    pdf.h2("Session ID flow")
    pdf.body(safe(
        "The frontend generates a UUID once at module load (lib/api.ts SESSION_ID) and sends "
        "it on every request as the X-Session-ID header. The backend's upsert_conversation "
        "treats session_id as a unique key: first request creates the Conversation row, "
        "subsequent requests within the same session attach Messages to it. This is what "
        "makes the chat history endpoint return a sensible thread without authentication."
    ))

    pdf.h2("Object storage: SeaweedFS")
    pdf.body(safe(
        "We landed on SeaweedFS instead of MinIO/S3 because it ships as three tiny Go binaries "
        "(master, volume, filer), needs almost no config, and gives us HTTP-native upload and "
        "fetch with directory-style paths. services/storage.py exposes a single save_bytes "
        "helper with explicit folder + ext arguments so the same code path serves both video "
        "and audio:"
    ))
    pdf.code(safe(
        "# Sign video\n"
        "await save_bytes(contents, file_id, 'video/mp4')\n"
        "# -> /videos/{file_id}.mp4 on the filer\n"
        "\n"
        "# TTS audio\n"
        "await save_bytes(audio_bytes, video_id, 'audio/mpeg', folder='audio', ext='mp3')\n"
        "# -> /audio/{video_id}.mp3 on the filer"
    ))

    pdf.h2("Silent data collection (collector.py)")
    pdf.body(safe(
        "Every successful inference appends a record to data/raw/inferences.jsonl with the "
        "video_id, gloss, english, confidence and a UTC timestamp. Every human correction "
        "(POST /sign/corrections) appends to data/raw/corrections.jsonl. The intent is to use "
        "this corpus post-hackathon to fine-tune a Qwen3-VL 7B LoRA on real, in-the-wild "
        "samples. The I/O is done with asyncio.to_thread so a slow disk never blocks the loop."
    ))

    # ── Page 14: Section 12 + 13 ──────────────────────────────────────────
    pdf.add_page()
    pdf.h1("12. Observability and Reliability")
    pdf.body(safe(
        "Even at 36 hours we wired up the full observability stack because demo failures are "
        "almost always 'something timed out and we don't know what'. The compose file ships "
        "Prometheus, Loki + Promtail, Grafana, and Langfuse for LLM tracing."
    ))
    pdf.bullets([
        safe("Prometheus: prometheus-fastapi-instrumentator exposes /metrics with default HTTP "
             "histograms. We can answer 'p95 latency of /sign/recognize' in real time."),
        safe("Loki + Promtail: docker logs stream into Loki via promtail mounting "
             "/var/run/docker.sock - Grafana shows them with structured fields."),
        safe("Langfuse: each Gemini call is wrapped in a Langfuse trace so we can see prompt + "
             "response + latency per sign, indexed by gloss for spot-checking."),
        safe("python-json-logger: every log line is structured JSON, which means we can grep "
             "with jq and aggregate in Loki without log-format gymnastics."),
        safe("Health endpoint: /api/v1/health verifies API key presence so the demo can fail "
             "loudly at startup instead of mysteriously at first inference."),
    ])

    pdf.h1("13. Latency Engineering: Hitting the 2-Second Bar")
    pdf.body(safe(
        "Two seconds end-to-end is the target. Below is the budget we measured - and the "
        "specific decisions taken to fit inside it."
    ))
    pdf.kv_table([
        ("Network upload (4MB H.264)", "~150ms"),
        ("API enqueues + 202 returned", "~50ms"),
        ("ffmpeg 480p transcode (worker)", "~250ms"),
        ("MediaPipe HandLandmarker VIDEO mode", "~400ms"),
        ("Gemini 2.5 Flash inline call", "~900ms"),
        ("ElevenLabs TTS (parallel-able, but serial today)", "~400ms"),
        ("Redis write + client poll round-trip", "~80ms"),
        ("Audio fetch + Audio.Sound.createAsync", "~200ms"),
        ("Total walltime visible to user", safe("~1.6 - 2.0 seconds")),
    ])
    pdf.h2("Optimisations that actually moved the needle")
    pdf.bullets([
        safe("Shared tmp volume between API and worker to skip the SeaweedFS round-trip."),
        safe("ffmpeg ultrafast preset + crf 28 - we trade visual quality for upload speed."),
        safe("Inline base64 video in Gemini call (skips Files API ACTIVE polling)."),
        safe("thinking_budget=0 - the single biggest Gemini latency win."),
        safe("MediaPipe face landmarks every 4th frame instead of every frame."),
        safe("ARQ keep_result=3600 + setex(3600) - results stay queryable for an hour even "
             "after the worker forgets them."),
        safe("Auto-play TTS on first poll where audio_url is truthy - removes a user tap."),
    ])

    # ── Page 15: Section 14 - Roadmap ─────────────────────────────────────
    pdf.add_page()
    pdf.h1("14. Roadmap and Post-Hackathon Plans")
    pdf.body(safe(
        "We deliberately scoped the hackathon build to be a credible demo, not a finished "
        "product. The roadmap below is what turns ASL Bridge into something you'd actually "
        "carry in your pocket."
    ))

    pdf.h2("Phase 2 - Real signing avatar (4-8 weeks)")
    pdf.body(safe(
        "Replace the embedded sign.mt iframe with a self-hosted avatar generation pipeline "
        "based on Wan 2.6 via FAL.AI. This unlocks expressive faces, signer customisation, and "
        "lets us cache common phrases as static MP4s for instant playback."
    ))

    pdf.h2("Phase 3 - Multi-language sign support (2-3 months)")
    pdf.body(safe(
        "Integrate SignLLM and Prompt2Sign so the system handles British SL, Chinese SL and "
        "Korean SL alongside ASL. The current Gemini prompt structure is generic enough that "
        "we can swap the closed-set vocabulary per locale and reuse the rest of the pipeline."
    ))

    pdf.h2("Phase 4 - Fine-tuned ASL recognition")
    pdf.body(safe(
        "Once enough corrections accumulate in data/raw/corrections.jsonl, we will fine-tune "
        "Qwen3-VL 7B with LoRA on (video, landmark JSON, gloss) triples. This is the path off "
        "the Gemini API for both cost and offline-capability reasons. The data pipeline is "
        "already collecting samples in the right format from day one."
    ))

    pdf.h2("Phase 5 - User accounts + offline mode")
    pdf.body(safe(
        "user_id on conversations is already nullable - a JWT middleware + users table is "
        "roughly half a day. After auth we can add shareable conversation links, multi-device "
        "sync, and an offline mode running the recogniser on-device via ONNX once the "
        "fine-tuned model fits in mobile memory."
    ))

    pdf.h2("Open questions we did not have time to answer")
    pdf.bullets([
        safe("Can we run MediaPipe on-device and avoid uploading the video? Probably, but the "
             "prompt currently relies on landmarks AND the full clip."),
        safe("Right chunking strategy for continuous, multi-sentence ASL? Today we expect "
             "single-utterance clips."),
        safe("Adversarial robustness: lighting, dark skin tones, partial occlusion, off-axis "
             "framing - none stress-tested yet."),
    ])

    # ── Page 16: Section 15 - Team ────────────────────────────────────────
    pdf.add_page()
    pdf.h1("15. Team, Credits and Closing Notes")
    pdf.body(safe(
        "ASL Bridge was built over 36 hours at ConHacks 2026 by a four-person team. Each "
        "engineer owned one slice of the system end-to-end, with a daily integration sync "
        "to keep the moving parts compatible."
    ))
    pdf.h2("Team")
    pdf.kv_table([
        ("Kai - Frontend",
         safe("Expo app, camera + mic flows, ElevenLabs TTS playback, three-tab navigation, "
              "session ID, animation WebView chrome injection, Voice Design page, "
              "SessionContext, history drawer, voice picker modal.")),
        ("Bob - Computer Vision",
         safe("OpenCV preprocessing, MediaPipe landmark sequences, face anchor design, "
              "velocity-based motion features.")),
        ("Max - UI / UX",
         safe("Design system, three-mode layout, confidence indicator, voice reasoning chips, "
              "demo polish, art direction, brand and visual identity.")),
        ("Dave - Backend + Models",
         safe("FastAPI + ARQ, Gemini prompt engineering, ElevenLabs STT + Voice Design API, "
              "conversation persistence, voice router, observability stack, data collection.")),
    ])

    pdf.h2("Acknowledgements")
    pdf.bullets([
        safe("Google MediaPipe team for the HandLandmarker and FaceLandmarker tasks - "
             "battery-efficient, ridiculously easy to integrate, runs everywhere."),
        safe("Google DeepMind for Gemini 2.5 Flash - the only frontier vision model with "
             "low enough latency for a real-time conversational demo."),
        safe("ElevenLabs for both Scribe (STT) and the Multilingual v2 voice that makes the "
             "demo feel human, not robotic."),
        safe("sign.mt for the open-source ASL avatar viewer that powers Phase 1 of the "
             "hearing-to-deaf path."),
        safe("The Expo team for making it possible for four engineers to ship a cross-platform "
             "mobile app inside a 36-hour window."),
    ])

    pdf.h2("Repository")
    pdf.body(safe(
        "Source: github.com/naik26m3/signly-conhacks-2026\n"
        "Backend Swagger: http://localhost:8000/docs\n"
        "Backend OpenAPI spec: http://localhost:8000/openapi.json\n"
        "Run locally: `docker compose up --build` (after copying .env.example to .env "
        "and filling in GEMINI_API_KEY + ELEVENLABS_API_KEY)."
    ))

    pdf.callout(
        "Closing thought",
        safe("The hard part was never any single component - MediaPipe is great, Gemini is "
             "great, ElevenLabs is great. The hard part was making them all finish in two "
             "seconds, persist properly, and feel like a conversation rather than a series "
             "of API calls. We think we got there. We hope you agree."),
    )

    # ── Save ───────────────────────────────────────────────────────────────
    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT))
    print(f"wrote {OUT}  ({OUT.stat().st_size} bytes, {pdf.page_no()} pages)")


if __name__ == "__main__":
    main()
