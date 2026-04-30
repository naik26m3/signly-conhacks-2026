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

  const send = useCallback(async (uri: string): Promise<UploadResult> => {
    setUpload({ kind: 'uploading' });

    const queued = await recognizeSign(uri);
    if (!queued.ok) {
      const errorResult: UploadResult = { kind: 'error', status: queued.status, message: queued.message };
      setUpload(errorResult);
      return errorResult;
    }

    const { video_id } = queued.data;
    setUpload({ kind: 'processing' });

    // Poll every 1.5s for up to 2 minutes.
    // If backend/worker is down, return a clear error instead of silent timeout.
    let lastPollError: string | undefined;
    for (let i = 0; i < 80; i++) {
      await new Promise((r) => setTimeout(r, 1500));
      const result = await getSignResult(video_id);
      if (!result.ok) {
        lastPollError = result.message;
        if (result.status === 404) {
          const notFoundResult: UploadResult = {
            kind: 'error',
            status: result.status,
            message:
              'Result not found while polling. Backend worker may not be running or the job expired.',
          };
          setUpload(notFoundResult);
          return notFoundResult;
        }
        continue;
      }
      if (result.data.status === 'done') {
        const successResult: UploadResult = { kind: 'success', status: result.status, data: result.data };
        setUpload(successResult);
        return successResult;
      }
      if (result.data.status === 'error') {
        const errorResult: UploadResult = { kind: 'error', message: result.data.detail ?? 'Processing failed' };
        setUpload(errorResult);
        return errorResult;
      }
    }
    const timeoutResult: UploadResult = {
      kind: 'error',
      message: lastPollError
        ? `Timed out waiting for result (120s). Last poll error: ${lastPollError}`
        : 'Timed out waiting for result (120s). Backend worker may be busy or not running.',
    };
    setUpload(timeoutResult);
    return timeoutResult;
  }, []);

  const reset = useCallback(() => setUpload({ kind: 'idle' }), []);
  return { upload, send, reset };
}
