# Frontend Dev Guide

React Native / Expo app. Uses the camera to record a sign, uploads it to the backend, and shows the recognised gloss.

## Quick start

```bash
cd frontend
cp .env.example .env        # edit EXPO_PUBLIC_API_URL (see below)
npm install
npx expo start
```

Scan the QR with **Expo Go** on your phone, or press `i`/`a` to open in a simulator.

## Environment

`frontend/.env`:
```
EXPO_PUBLIC_API_URL=http://<your-machine-ip>:18000
```

- Use your **LAN IP** (e.g. `192.168.x.x`), not `localhost` — the phone needs to reach your machine.
- If you're using an ngrok tunnel, paste the https URL here instead.
- The backend runs on port `18000` (mapped in docker-compose).

## Project layout

```
app/
  index.tsx           — main screen (wires camera → upload → preview)
  _layout.tsx         — root layout / navigation shell
components/
  camera-recorder.tsx — front-facing camera, tap to record / tap again to stop
  video-preview.tsx   — plays back the clip, shows upload/processing/result states
  permissions-gate.tsx— asks for camera + mic permissions before rendering children
hooks/
  use-video-upload.ts — manages the full upload + polling lifecycle
lib/
  api.ts              — typed API client, all backend calls live here
constants/
  theme.ts            — shared colours/spacing
```

## Communication modes

| Mode | Who uses it | Flow |
|------|-------------|------|
| **Deaf Mode** | Deaf / ASL user | Records sign → backend recognises → returns gloss + english + **audio** → auto-plays audio so hearing person hears it |
| **Hearing Mode** | Hearing person | Records voice → backend transcribes → returns transcript + ASL gloss → displayed as large readable text for deaf person |

## How the sign recognition flow works (Deaf Mode)

1. `CameraRecorder` records a clip → calls `onRecorded(uri)` with the local file URI.
2. `index.tsx` / `deaf.tsx` switches to `VideoPreview`, passing the URI and the `upload` state.
3. User taps **Recognise Sign** → `send(uri)` is called on `useVideoUpload`, with `X-Session-ID` header.
4. Hook uploads the video (`POST /api/v1/sign/recognize`) — backend returns `202 { video_id }` immediately.
5. Hook polls `GET /api/v1/sign/result/{video_id}` every 1.5 s for up to 45 s.
6. When `status === "done"`, `upload` becomes `{ kind: 'success', data: { gloss, english, confidence, landmarks_found, audio_url } }`.
7. Screen renders gloss (large) + english (smaller).
8. **If `audio_url` is present, auto-play audio immediately** (hearing person hears the signed message spoken aloud). Show a replay button for on-demand replay.

Upload state machine (from `use-video-upload.ts`):
```
idle → uploading → processing → success
                              → error
```

## How the speech transcription flow works (Hearing Mode)

1. `use-record.ts` records mic audio via `expo-av`.
2. On stop: `POST /api/v1/speech/transcribe` with the audio file.
3. Backend returns `{ transcript, gloss }` — **no audio generated on this side** (hearing person already spoke).
4. Screen displays transcript + gloss in large, deaf-readable text.

## Audio playback

Use `expo-av` `Audio.Sound` to play `audio_url` directly from SeaweedFS — no need to download:

```ts
import { Audio } from 'expo-av';

const { sound } = await Audio.Sound.createAsync({ uri: audio_url });
await sound.playAsync();
// unload when done to free memory
sound.setOnPlaybackStatusUpdate((s) => {
  if (s.isLoaded && s.didJustFinish) sound.unloadAsync();
});
```

## Session ID

Each install generates a UUID once and persists it in `AsyncStorage` (see `lib/session.ts`). It is sent on every sign recognition request as the `X-Session-ID` header and used to fetch history.

```ts
import { getSessionId } from '@/lib/session';
const sessionId = await getSessionId();
```

## History screen (`app/history.tsx`)

Calls `GET /api/v1/history?session_id=<id>` and renders a flat list of past sign recognitions. Each item shows gloss, english, timestamp, and a play button that plays `audio_url` via `expo-av`.

## Adding a new screen

The app uses **Expo Router** (file-based routing). Create a file under `app/` and it becomes a route:

```
app/history.tsx   →  accessible at route /history
```

Link to it with `<Link href="/history">` or `router.push('/history')`.

## Adding a new API call

All backend calls go in `lib/api.ts`. The `api` helper handles base URL, headers, and JSON parsing:

```ts
// GET example
export function getSomething(id: string) {
  return api.get<MyResponseType>(`/api/v1/something/${id}`);
}

// POST JSON example
export function createSomething(payload: MyPayload) {
  return api.postJson<MyResponseType>('/api/v1/something', payload);
}
```

Return type is always `ApiResult<T>` — check `.ok` before accessing `.data`:

```ts
const result = await getSomething(id);
if (!result.ok) { /* result.message has the error */ return; }
console.log(result.data);
```

## Running on a physical device

Expo Go works for most development. If you need a native build (e.g. camera issues on Android):

```bash
npx expo run:android   # needs Android Studio + connected device / emulator
npx expo run:ios       # macOS + Xcode only
```

## Common issues

| Problem | Fix |
|---|---|
| Camera black screen | Make sure you're on a real device or simulator with camera support; check `PermissionsGate` granted camera + mic |
| `EXPO_PUBLIC_API_URL is not set` | You're missing `frontend/.env` — copy from `.env.example` |
| Network request fails on device | Use your LAN IP in `.env`, not `localhost` |
| `ngrok-skip-browser-warning` header | Already added in `api.ts` — ngrok tunnels work out of the box |
