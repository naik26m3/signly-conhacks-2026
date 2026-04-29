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
    let data: any = text;
    try { data = JSON.parse(text); } catch { /* keep as text */ }

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

// ── endpoints ─────────────────────────────────────────────────────────────

export type UploadVideoResponse = {
  api_version: string;
  video_id: string;
  status: string;
};

export function uploadVideo(uri: string) {
  const formData = new FormData();
  formData.append('file', { uri, type: 'video/mp4', name: 'upload.mp4' } as any);
  return api.post<UploadVideoResponse>('/api/v1/uploads/video', formData);
}
