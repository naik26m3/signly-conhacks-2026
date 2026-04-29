# Frontend Plan — Kai

Expo React Native app for ASL Bridge. See `docs/PLAN.md` for system architecture and API overview.

---

## File Structure

```
frontend/
├── app/
│   ├── _layout.tsx        # Root layout, navigation shell
│   ├── index.tsx          # Home — mode selector
│   ├── deaf.tsx           # Deaf Mode — camera + result display
│   └── hearing.tsx        # Hearing Mode — mic + gloss display
├── components/
│   ├── mode-card.tsx      # Home screen mode selector card
│   ├── result-banner.tsx  # Gloss + English result display
│   ├── confidence-badge.tsx # "signing..." vs confirmed state
│   └── record-button.tsx  # Shared record/stop button
├── services/
│   └── api.ts             # All fetch calls to backend
├── constants/
│   └── theme.ts           # Colors, typography (from Max)
├── hooks/
│   └── use-record.ts      # Shared recording logic
└── app.json               # extra.apiUrl set here
```

---

## Tasks

### Setup
- [ ] Confirm Expo Router is configured (`app/` directory routing)
- [ ] Set `extra.apiUrl` in `app.json` pointing to backend
- [ ] `constants/theme.ts` — implement Max's design tokens (colors, fonts, spacing)
- [ ] Install dependencies: `expo-camera`, `expo-av`, `expo-speech`, `react-native-reanimated`

### Home screen (`app/index.tsx`)
- [ ] Two mode cards: Deaf Mode and Hearing Mode
- [ ] Navigate to `app/deaf.tsx` or `app/hearing.tsx` on tap
- [ ] Dark background, large readable text (Max's layout)

### Deaf Mode (`app/deaf.tsx`)
- [ ] Front camera live preview via `expo-camera`
- [ ] Record button — start/stop video recording with `expo-av` `recordAsync()`
- [ ] On stop: upload video via `FormData` POST to `/api/v1/asl/recognize`
- [ ] Show `confidence-badge` ("signing...") while request is in flight
- [ ] On response: display `gloss` and `english` in `result-banner`
- [ ] On `english` received: call ElevenLabs TTS to speak aloud
- [ ] `AbortController` — cancel request on screen unmount

### Hearing Mode (`app/hearing.tsx`)
- [ ] Mic record button — start/stop audio recording with `expo-av`
- [ ] On stop: upload audio via `FormData` POST to `/api/v1/speech/transcribe`
- [ ] Show loading state while request is in flight
- [ ] On response: display `gloss` in large text (deaf-readable)
- [ ] `AbortController` — cancel request on screen unmount

### Shared components
- [ ] `record-button.tsx` — animated pulse while recording (Reanimated `useSharedValue`)
- [ ] `result-banner.tsx` — shows gloss (large) and English (smaller) with fade-in animation
- [ ] `confidence-badge.tsx` — "signing..." spinner vs confirmed label
- [ ] `mode-card.tsx` — home screen card with icon + label

### API service (`services/api.ts`)
- [ ] `recognizeSign(videoUri)` → POST to `/api/v1/asl/recognize` → `{ gloss, english, confidence }`
- [ ] `transcribeSpeech(audioUri)` → POST to `/api/v1/speech/transcribe` → `{ transcript, gloss }`
- [ ] Base URL from `Constants.expoConfig.extra.apiUrl`
- [ ] All functions accept `AbortSignal` for cancellation

### Custom hook (`hooks/use-record.ts`)
- [ ] `useRecord()` — encapsulates `expo-av` recording setup, start, stop, cleanup
- [ ] Returns `{ isRecording, startRecording, stopRecording, uri }`

---

## Notes

- No hardcoded colors — always use `constants/theme.ts` tokens
- All API responses are text strings for now — no video/avatar yet
- ElevenLabs TTS replaces `expo-speech` — use ElevenLabs SDK or REST API
- Test on both iOS and Android via Expo Go before calling anything done
