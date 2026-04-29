# Frontend Plan — Kai

Expo React Native app for ASL Bridge. See `docs/PLAN.md` for system architecture and API overview.

---

## File Structure

```
frontend/
├── app/
│   ├── _layout.tsx            # Root layout, navigation shell
│   ├── index.tsx              # Current: record → preview → upload flow  ✓
│   ├── deaf.tsx               # Deaf Mode screen  [ ]
│   └── hearing.tsx            # Hearing Mode screen  [ ]
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
│   └── api.ts                 # Typed API client + all endpoints  ✓
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
- [ ] On stop: call `api.recognizeSign(videoUri)`
- [ ] Show `confidence-badge` ("signing...") while in flight
- [ ] On response: display `gloss` + `english` in `result-banner`
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

### Hook
- [ ] `hooks/use-record.ts` — wraps expo-av recording: `{ isRecording, startRecording, stopRecording, uri }`

### API endpoints to add to `lib/api.ts`
- [ ] `recognizeSign(videoUri)` → POST `/api/v1/sign/recognize` → `{ gloss, english, confidence }`
- [ ] `transcribeSpeech(audioUri)` → POST `/api/v1/speech/transcribe` → `{ transcript, gloss }`
- [ ] Pass `AbortSignal` through to `request()` for cancellation

---

## Notes

- No hardcoded colors — use a `constants/theme.ts` once Max finalises design tokens
- All API responses are text strings for now — no video/avatar yet
- Test on iOS via Expo Go (tunnel mode: `npx expo start --tunnel`) before calling done
