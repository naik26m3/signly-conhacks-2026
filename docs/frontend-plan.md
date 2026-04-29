# Frontend Plan — Kai

Expo React Native app for ASL Bridge. See `docs/PLAN.md` for system architecture and API overview.

---

## File Structure

```
frontend/
├── app/
│   ├── _layout.tsx            # Root layout, navigation shell
│   ├── index.tsx              # Home: mode selector (Deaf / Hearing)  [ ]
│   ├── deaf.tsx               # Deaf Mode: sign → text + audio playback  [ ]
│   ├── hearing.tsx            # Hearing Mode: voice → transcript + gloss  [ ]
│   └── history.tsx            # History: past recognitions with audio replay  [ ]
├── components/
│   ├── camera-recorder.tsx    # CameraView + record/stop  ✓
│   ├── video-preview.tsx      # VideoView + upload result panel  ✓
│   ├── permissions-gate.tsx   # Camera/mic/media permission wrapper  ✓
│   ├── result-banner.tsx      # Gloss + English result display  [ ]
│   ├── confidence-badge.tsx   # "signing..." spinner vs confirmed  [ ]
│   └── record-button.tsx      # Animated pulse record button  [ ]
├── hooks/
│   ├── use-video-upload.ts    # Upload state machine (idle/uploading/success/error)  ✓
│   └── use-record.ts          # expo-av recording setup, start, stop, cleanup  [ ]
├── lib/
│   ├── api.ts                 # Typed API client + all endpoints  ✓
│   └── session.ts             # Generate + persist session UUID in AsyncStorage  [ ]
└── app.json
```

API base URL comes from `EXPO_PUBLIC_API_URL` in `frontend/.env` (not `app.json`).

---

## What's Done ✓

- `lib/api.ts` — generic `request()` helper + `uploadVideo()` endpoint
- `hooks/use-video-upload.ts` — upload state machine
- `components/permissions-gate.tsx` — camera + mic + media permissions
- `components/camera-recorder.tsx` — record/stop video
- `components/video-preview.tsx` — preview + inline upload result (spinner / success / error)
- `app/index.tsx` — thin coordinator: permissions → record → preview/upload

---

## What's Left [ ]

### Home screen — mode selector (`app/index.tsx` → refactor or new screen)
- [ ] Two mode cards: **Deaf Mode** and **Hearing Mode**
- [ ] Navigate to `app/deaf.tsx` or `app/hearing.tsx` on tap
- [ ] Dark background, large readable text

### Deaf Mode (`app/deaf.tsx`)
- [ ] Reuse `camera-recorder.tsx` for video capture
- [ ] On stop: call `api.recognizeSign(videoUri, sessionId)` with `X-Session-ID` header
- [ ] Show `confidence-badge` ("signing...") while in flight
- [ ] On response: display `gloss` + `english` in `result-banner`
- [ ] **If `audio_url` present: auto-play audio via `expo-av` so hearing person hears it**
- [ ] Show replay (speaker) button for on-demand replay
- [ ] `AbortController` on screen unmount

### Hearing Mode (`app/hearing.tsx`)
- [ ] Mic record button using `use-record.ts`
- [ ] On stop: call `api.transcribeSpeech(audioUri)`
- [ ] Show loading state while in flight
- [ ] On response: display `gloss` in large text (deaf-readable)
- [ ] `AbortController` on screen unmount

### Shared components
- [ ] `record-button.tsx` — animated pulse while recording (Reanimated `useSharedValue`)
- [ ] `result-banner.tsx` — gloss (large) + English (smaller) with fade-in animation
- [ ] `confidence-badge.tsx` — "signing..." spinner vs confirmed label

### History Screen (`app/history.tsx`)
- [ ] On mount: load `session_id` from `lib/session.ts`
- [ ] Call `api.getConversationMessages(sessionId)` → chat thread ordered oldest-first
- [ ] Render chat bubbles: `deaf_to_hearing` on right, `hearing_to_deaf` on left
- [ ] `deaf_to_hearing` bubble: gloss (bold) + english + speaker icon → `Audio.Sound.createAsync({ uri: item.audio_url })` → `playAsync()`
- [ ] `hearing_to_deaf` bubble: transcript + gloss (smaller), no audio button
- [ ] Unload sound on playback finish to free memory

### Session utility (`lib/session.ts`)
- [ ] `getSessionId()` — reads UUID from `AsyncStorage`, generates + saves on first call

### Hook
- [ ] `hooks/use-record.ts` — wraps expo-av recording: `{ isRecording, startRecording, stopRecording, uri }`

### API endpoints to add to `lib/api.ts`
- [ ] `recognizeSign(videoUri, sessionId)` → POST `/api/v1/sign/recognize` (header `X-Session-ID`) → `{ gloss, english, confidence, audio_url }`
- [ ] `transcribeSpeech(audioUri, sessionId)` → POST `/api/v1/speech/transcribe` (header `X-Session-ID`) → `{ transcript, gloss }`
- [ ] `getConversationMessages(sessionId, limit?)` → GET `/api/v1/conversations/{sessionId}/messages` → `{ conversation_id, total, messages[] }`
- [ ] Pass `AbortSignal` through to `request()` for cancellation

---

## Notes

- No hardcoded colors — use a `constants/theme.ts` once Max finalises design tokens
- All API responses are text strings for now — no video/avatar yet
- Test on iOS via Expo Go (tunnel mode: `npx expo start --tunnel`) before calling done
