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

export const SESSION_ID: string = (() => {
  // stable random UUID for this install — persists as module-level constant
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });
})();

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
    headers: { 'X-Session-ID': SESSION_ID },
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
  const formData = new FormData();
  formData.append('file', { uri, type: 'audio/m4a', name: 'speech.m4a' } as any);
  return api.post<TranscribeResponse>('/api/v1/speech/transcribe', formData, {
    headers: { 'X-Session-ID': SESSION_ID },
  });
}

export function getGloss(text: string) {
  return api.postJson<GlossResponse>('/api/v1/speech/gloss', { text });
}
