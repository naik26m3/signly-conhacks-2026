import { useCallback, useState } from 'react';
import { uploadVideo, type ApiResult } from '@/lib/api';

export type UploadResult =
  | { kind: 'idle' }
  | { kind: 'uploading' }
  | { kind: 'success'; status: number; data: any }
  | { kind: 'error'; status?: number; message: string };

const adapt = (r: ApiResult): UploadResult =>
  r.ok
    ? { kind: 'success', status: r.status, data: r.data }
    : { kind: 'error', status: r.status, message: r.message };

export function useVideoUpload() {
  const [upload, setUpload] = useState<UploadResult>({ kind: 'idle' });

  const send = useCallback(async (uri: string) => {
    setUpload({ kind: 'uploading' });
    const result = await uploadVideo(uri);
    setUpload(adapt(result));
  }, []);

  const reset = useCallback(() => setUpload({ kind: 'idle' }), []);

  return { upload, send, reset };
}
