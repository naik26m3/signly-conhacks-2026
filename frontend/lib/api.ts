export const API_URL: string = process.env.EXPO_PUBLIC_API_URL ?? '';

if (!API_URL) {
  throw new Error('EXPO_PUBLIC_API_URL is not set — add it to frontend/.env and restart Expo');
}

export type ApiResult<T = any> =
  | { ok: true; status: number; data: T }
  | { ok: false; status?: number; message: string };

async function request<T = any>(path: string, init: RequestInit = {}): Promise<ApiResult<T>> {
  const headers = {
    'ngrok-skip-browser-warning': 'true',
    ...(init.headers ?? {}),
  };

  try {
    const response = await fetch(`${API_URL}${path}`, { ...init, headers });
    const text = await response.text();
    const contentType = response.headers.get('content-type') ?? '';
    let data: any = text;
    try { data = JSON.parse(text); } catch { /* keep as text */ }

    // Ngrok/browser interstitial or tunnel 404 often returns HTML instead of API JSON.
    if (contentType.includes('text/html')) {
      const looksLikeNgrokPage =
        typeof text === 'string' &&
        (text.includes('assets.ngrok.com') ||
          text.includes('<!DOCTYPE html>') ||
          text.includes('ngrok'));

      if (looksLikeNgrokPage) {
        return {
          ok: false,
          status: response.status,
          message:
            'API URL is pointing to an ngrok HTML page, not the backend API. Check EXPO_PUBLIC_API_URL and ensure tunnel forwards to backend port 18000.',
        };
      }
    }

    if (response.ok) {
      return { ok: true, status: response.status, data };
    }
    return {
      ok: false,
      status: response.status,
      message:
        typeof data === 'object' && data?.detail
          ? String(data.detail)
          : typeof data === 'string' && data.length > 0
          ? data.slice(0, 500)
          : `HTTP ${response.status}`,
    };
  } catch (error: any) {
    return { ok: false, message: error?.message ?? 'Network request failed' };
  }
}

export const api = {
  get: <T = any>(path: string, init?: RequestInit) =>
    request<T>(path, { ...init, method: 'GET' }),
  post: <T = any>(path: string, body?: any, init?: RequestInit) =>
    request<T>(path, { ...init, method: 'POST', body }),
  postJson: <T = any>(path: string, json: any, init?: RequestInit) =>
    request<T>(path, {
      ...init,
      method: 'POST',
      body: JSON.stringify(json),
      headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    }),
};

// Session ID is mutable so callers can start a fresh "thread" without auth —
// TranslatePage calls resetSession() on mount so each visit = new conversation.
function _newSessionId(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });
}

let _sessionId = _newSessionId();
export const getSessionId = (): string => _sessionId;
export const resetSession = (): string => {
  _sessionId = _newSessionId();
  return _sessionId;
};
// Restore a previously-used session id when the UI switches back to an
// older conversation. Backend tmp files may have been cleared, but the
// Conversation row keyed by this id should still exist.
export const setSessionId = (sid: string): void => {
  _sessionId = sid;
};

// ── endpoints ─────────────────────────────────────────────────────────────

export type QueuedResponse = {
  api_version: string;
  video_id: string;
  status: 'processing';
};

export type SignResultResponse = {
  api_version: string;
  video_id: string;
  status: 'done' | 'error' | 'processing';
  gloss?: string;
  english?: string;
  confidence?: number;
  landmarks_found?: boolean;
  audio_url?: string;
  detail?: string;
};

export function getAudioUrl(videoId: string): string {
  return `${API_URL}/api/v1/sign/audio/${videoId}`;
}

export function recognizeSign(uri: string) {
  const formData = new FormData();
  formData.append('file', { uri, type: 'video/quicktime', name: 'sign.mov' } as any);
  return api.post<QueuedResponse>('/api/v1/sign/recognize', formData, {
    headers: { 'X-Session-ID': getSessionId() },
  });
}

export type DetectHandsResponse = { hands_detected: boolean };

export function detectHands(uri: string) {
  const formData = new FormData();
  formData.append('file', { uri, type: 'video/quicktime', name: 'sign.mov' } as any);
  return api.post<DetectHandsResponse>('/api/v1/sign/detect-hands', formData);
}

export function getSignResult(videoId: string) {
  return api.get<SignResultResponse>(`/api/v1/sign/result/${videoId}`);
}

// ── speech ─────────────────────────────────────────────────────────────────

export type TranscribeResponse = { transcript: string };
export type GlossResponse = { gloss: string };

export function transcribeAudio(uri: string) {
  // expo-av's HIGH_QUALITY preset produces .m4a on iOS but .mp4 on Android.
  // Match the MIME type to the actual file extension so ElevenLabs scribe accepts it.
  const lower = uri.toLowerCase();
  let ext = 'm4a';
  let type = 'audio/m4a';
  if (lower.endsWith('.mp4'))      { ext = 'mp4';  type = 'audio/mp4'; }
  else if (lower.endsWith('.wav')) { ext = 'wav';  type = 'audio/wav'; }
  else if (lower.endsWith('.webm')){ ext = 'webm'; type = 'audio/webm'; }
  else if (lower.endsWith('.aac')) { ext = 'aac';  type = 'audio/aac'; }
  else if (lower.endsWith('.mp3')) { ext = 'mp3';  type = 'audio/mpeg'; }

  const formData = new FormData();
  formData.append('file', { uri, type, name: `speech.${ext}` } as any);
  return api.post<TranscribeResponse>('/api/v1/speech/transcribe', formData, {
    headers: { 'X-Session-ID': getSessionId() },
  });
}

export function getGloss(text: string) {
  return api.postJson<GlossResponse>('/api/v1/speech/gloss', { text });
}

// ── conversation title ────────────────────────────────────────────────────

export type ConversationTitleResponse = {
  api_version: string;
  title: string;
};

export function getConversationTitle(sessionId: string) {
  return api.get<ConversationTitleResponse>(`/api/v1/conversations/${sessionId}/title`);
}

// ── voice design (ElevenLabs via Gemini) ───────────────────────────────────

export type VoiceDesignParams = {
  voice_description: string;
  display_label: string;
  tags: string[];
};

export type VoiceDesignResponse = {
  api_version: string;
  params: VoiceDesignParams;
  sample_text: string;
  audio_base64: string;
  audio_mime: string;
};

export function designVoice(message: string) {
  return api.postJson<VoiceDesignResponse>('/api/v1/voice/design', { message });
}

export type VoiceSpeakResponse = {
  api_version: string;
  audio_base64: string;
  audio_mime: string;
};

export function speakWithDesignedVoice(voiceDescription: string, text: string) {
  return api.postJson<VoiceSpeakResponse>('/api/v1/voice/speak', {
    voice_description: voiceDescription,
    text,
  });
}
