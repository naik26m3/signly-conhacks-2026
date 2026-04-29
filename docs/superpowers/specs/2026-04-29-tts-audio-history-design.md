# TTS Audio Generation + Conversation History Design

**Date:** 2026-04-29
**Status:** Approved

---

## Problem

Sign recognition returns text (gloss + english) but no audio, so the hearing person has to read the result instead of hearing it spoken. There is also no record of past conversations for either party to replay.

---

## Communication Directions

| Direction | Flow | Output |
|-----------|------|--------|
| Deaf → Hearing | Video → hand tracking + Gemini → english text → **ElevenLabs TTS → audio** | Hearing person hears the signed message spoken aloud |
| Hearing → Deaf | Audio → ElevenLabs STT → transcript + ASL gloss | Deaf person reads the transcript; gloss used later to drive avatar |

TTS lives in the **sign recognition worker** only. The `/speech/transcribe` endpoint does not synthesize audio — the hearing person is already speaking.

---

## Data Model

Two tables, one-to-many relationship — same pattern as any chat app (ChatGPT style).

### `conversations`

One row per chat session. Groups all messages between the two parties.

```sql
CREATE TABLE conversations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id  UUID NOT NULL UNIQUE,   -- client-generated, one per device install
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    user_id     UUID NULL               -- FK to users once auth lands
);

CREATE INDEX ON conversations (session_id);
```

### `messages`

One row per turn — either a signed message or a spoken message.

```sql
CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    direction       TEXT NOT NULL,   -- 'deaf_to_hearing' | 'hearing_to_deaf'
    content         TEXT NOT NULL,   -- english text (deaf side) or transcript (hearing side)
    gloss           TEXT,            -- ASL gloss for both directions
    audio_url       TEXT,            -- SeaweedFS URL, only for deaf_to_hearing TTS audio
    confidence      FLOAT,           -- sign recognition confidence, only for deaf_to_hearing
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ON messages (conversation_id, created_at ASC);
```

`user_id` on `conversations` is nullable now. When auth is added, a migration links users to existing conversations via `session_id`.

---

## Architecture

### Worker Changes (`worker.py`)

After Gemini returns `english` text, the worker runs TTS + DB writes before writing the Redis result:

```
process_sign_video(video_id, content_type, session_id):
  1. Download video from SeaweedFS
  2. Hand tracking → frame_b64
  3. Gemini → { gloss, english, confidence }
  4. ElevenLabs TTS(english) → audio_bytes                      ← new
  5. Save audio_bytes to SeaweedFS /audio/{video_id}.mp3         ← new
  6. Upsert conversation row for session_id                      ← new
  7. Insert message row (direction='deaf_to_hearing')            ← new
  8. Write Redis: { status, gloss, english, confidence,
                    landmarks_found, audio_url }                 ← audio_url is new
```

`session_id` comes from the client via `X-Session-ID` header on `POST /api/v1/sign/recognize`, forwarded to the ARQ job payload.

### Speech Transcribe Changes (`routers/speech.py`)

After ElevenLabs STT returns the transcript, also insert a message row:

```
POST /api/v1/speech/transcribe:
  1. ElevenLabs STT → transcript
  2. Gemini → gloss                                              (existing)
  3. Upsert conversation row for session_id                      ← new
  4. Insert message row (direction='hearing_to_deaf')            ← new
  5. Return { transcript, gloss }                                (existing)
```

`session_id` comes from `X-Session-ID` header, same as sign recognize.

### SeaweedFS Audio Path

```
/audio/{video_id}.mp3
```

Same filer URL pattern as `/videos/{video_id}.mp4`. `audio_url` stored in DB and returned to client is the full filer URL.

---

## API Changes

### `POST /api/v1/sign/recognize`

**New header (optional — backend generates a UUID if missing):**
```
X-Session-ID: <client-generated UUID>
```

Response unchanged — still `202 { video_id, status: "processing" }`.

### `POST /api/v1/speech/transcribe`

**New header (optional — backend generates a UUID if missing):**
```
X-Session-ID: <client-generated UUID>
```

Response unchanged — still `{ transcript, gloss }`.

### `GET /api/v1/sign/result/{video_id}`

`SignResultResponse` gains one new optional field:

```json
{
  "status": "done",
  "gloss": "HELLO",
  "english": "Hello",
  "confidence": 0.92,
  "landmarks_found": true,
  "audio_url": "http://<filer>/audio/<video_id>.mp3"
}
```

`audio_url` is `null` if TTS synthesis failed — recognition result is still delivered.

### `GET /api/v1/conversations/{session_id}/messages`

Returns all messages in a conversation, ordered oldest-first (chat thread order).

**Path param:** `session_id` — UUID string

**Query params:**
- `limit` (optional, default 50, max 200)
- `before` (optional) — UUID of a message, for pagination (fetch messages older than this)

**Response:**

```json
{
  "api_version": "v1",
  "conversation_id": "...",
  "total": 12,
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

## New Files

| File | Purpose |
|------|---------|
| `backend/routers/conversations.py` | `GET /api/v1/conversations/{session_id}/messages` |
| `backend/schemas/conversation.py` | `MessageItem`, `ConversationMessagesResponse` Pydantic models |
| `backend/services/conversation.py` | DB upsert/insert helpers used by worker + speech router |
| `backend/migrations/versions/<hash>_add_conversations_messages.py` | Alembic migration |

## Modified Files

| File | Change |
|------|--------|
| `backend/worker.py` | TTS + SeaweedFS audio save + conversation/message DB insert |
| `backend/routers/speech.py` | Read `X-Session-ID`, insert hearing_to_deaf message row |
| `backend/routers/sign.py` | Forward `X-Session-ID` header to ARQ job payload |
| `backend/services/storage.py` | Add `save_audio_bytes()` for `/audio/` path |
| `backend/schemas/sign.py` | `SignResultResponse` gains `audio_url: str \| None` |
| `backend/server.py` | Include `conversations` router |

---

## Error Handling

- **TTS fails** — log warning, `audio_url = None` in Redis result, message row still inserted without audio_url. Recognition result still delivered.
- **DB insert fails** — log warning, do not fail the job. Audio file still saved, URL still returned to client. Row can be retried.
- **SeaweedFS audio save fails** — log error, `audio_url = None`. Does not block recognition result.

---

## Frontend — What to Render

### Chat thread (active conversation screen)

Render messages as a vertical chat thread, newest at the bottom:

| Direction | Bubble side | Shows |
|-----------|-------------|-------|
| `deaf_to_hearing` | Right | Gloss (bold) + english text + speaker icon (replay TTS audio) |
| `hearing_to_deaf` | Left | Transcript text + gloss (smaller, below) |

Auto-play `audio_url` immediately when a new `deaf_to_hearing` result arrives. Show a speaker icon on the bubble for on-demand replay.

```ts
// play audio from a SeaweedFS URL
const { sound } = await Audio.Sound.createAsync({ uri: message.audio_url });
await sound.playAsync();
sound.setOnPlaybackStatusUpdate((s) => {
  if (s.isLoaded && s.didJustFinish) sound.unloadAsync();
});
```

### Deaf Mode flow

1. User records sign → `POST /api/v1/sign/recognize` with `X-Session-ID` header
2. Poll for result → on `status === "done"`, append `deaf_to_hearing` bubble to thread
3. Auto-play `audio_url`

### Hearing Mode flow

1. User records voice → `POST /api/v1/speech/transcribe` with `X-Session-ID` header
2. Response arrives immediately → append `hearing_to_deaf` bubble to thread
3. No audio playback (hearing person already spoke)

### History / past conversations

- Load thread on mount: `GET /api/v1/conversations/{session_id}/messages`
- Render full thread with replay buttons on each `deaf_to_hearing` bubble

### New API calls (`lib/api.ts`)

```ts
export type MessageItem = {
  id: string;
  direction: 'deaf_to_hearing' | 'hearing_to_deaf';
  content: string;
  gloss: string | null;
  audio_url: string | null;
  confidence: number | null;
  created_at: string;
};

export type ConversationMessagesResponse = {
  api_version: string;
  conversation_id: string;
  total: number;
  messages: MessageItem[];
};

export function getConversationMessages(sessionId: string, limit = 50) {
  return api.get<ConversationMessagesResponse>(
    `/api/v1/conversations/${sessionId}/messages?limit=${limit}`
  );
}
```

### Session ID (`lib/session.ts`)

Generated once on first app launch, persisted in `AsyncStorage`. Sent as `X-Session-ID` on every request.

```ts
import AsyncStorage from '@react-native-async-storage/async-storage';
import 'react-native-get-random-values';
import { v4 as uuidv4 } from 'uuid';

const KEY = 'signly_session_id';

export async function getSessionId(): Promise<string> {
  let id = await AsyncStorage.getItem(KEY);
  if (!id) { id = uuidv4(); await AsyncStorage.setItem(KEY, id); }
  return id;
}
```

---

## What Is NOT in Scope

- Auth / user accounts — `user_id` on `conversations` is nullable, wired up later
- Multiple conversations per user — one conversation per `session_id` for now
- Avatar / ASL movement generation — future add-on
- TTS for the hearing → deaf direction — hearing person already speaks
- Cursor-based pagination (the `before` param is defined but not required for MVP)
