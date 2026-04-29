import { useCallback, useState } from 'react';
import { recognizeSign, getSignResult, type SignResultResponse } from '@/lib/api';

export type UploadResult =
  | { kind: 'idle' }
  | { kind: 'uploading' }
  | { kind: 'processing' }
  | { kind: 'success'; status: number; data: SignResultResponse }
  | { kind: 'error'; status?: number; message: string };

export function useVideoUpload() {
  const [upload, setUpload] = useState<UploadResult>({ kind: 'idle' });

  const send = useCallback(async (uri: string) => {
    setUpload({ kind: 'uploading' });

    const queued = await recognizeSign(uri);
    if (!queued.ok) {
      setUpload({ kind: 'error', status: queued.status, message: queued.message });
      return;
    }

    const { video_id } = queued.data;
    setUpload({ kind: 'processing' });

    // Poll every 1.5s for up to 45 seconds
    for (let i = 0; i < 30; i++) {
      await new Promise((r) => setTimeout(r, 1500));
      const result = await getSignResult(video_id);
      if (!result.ok) continue;
      if (result.data.status === 'done') {
        setUpload({ kind: 'success', status: result.status, data: result.data });
        return;
      }
      if (result.data.status === 'error') {
        setUpload({ kind: 'error', message: result.data.detail ?? 'Processing failed' });
        return;
      }
    }
    setUpload({ kind: 'error', message: 'Timed out waiting for result (45s)' });
  }, []);

  const reset = useCallback(() => setUpload({ kind: 'idle' }), []);
  return { upload, send, reset };
}
