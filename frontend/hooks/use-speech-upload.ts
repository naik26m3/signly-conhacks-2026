import { transcribeAudio, getGloss } from '@/lib/api';
import { Audio } from 'expo-av';
import { useCallback, useEffect, useRef, useState } from 'react';

export type SpeechResult = { transcript: string; gloss: string; audioUri: string };

// Module-level: when a hook unmounts mid-recording, its async cleanup is stored here
// so the next page's start() can await it before grabbing the mic.
let pendingCleanup: Promise<void> | null = null;

const SPEECH_RECORDING_OPTIONS: Audio.RecordingOptions = {
  ...Audio.RecordingOptionsPresets.HIGH_QUALITY,
  android: {
    ...Audio.RecordingOptionsPresets.HIGH_QUALITY.android,
    numberOfChannels: 1,
    bitRate: 64000,
  },
  ios: {
    ...Audio.RecordingOptionsPresets.HIGH_QUALITY.ios,
    numberOfChannels: 1,
    bitRate: 64000,
  },
};

export function useSpeechUpload() {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [recordingUri, setRecordingUri] = useState<string | null>(null);
  const recordingRef = useRef<Audio.Recording | null>(null);
  const isStartingRef = useRef(false);

  useEffect(() => {
    return () => {
      const recording = recordingRef.current;
      recordingRef.current = null;
      pendingCleanup = (async () => {
        if (recording) {
          try { await recording.stopAndUnloadAsync(); } catch {}
        }
        try { await Audio.setAudioModeAsync({ allowsRecordingIOS: false }); } catch {}
      })();
    };
  }, []);

  const cleanupRecording = useCallback(async () => {
    const recording = recordingRef.current;
    recordingRef.current = null;
    if (!recording) return;

    try {
      const status = await recording.getStatusAsync();
      if (status.canRecord) {
        await recording.stopAndUnloadAsync();
      }
    } catch {
      try { await recording.stopAndUnloadAsync(); } catch {}
    }
  }, []);

  const start = useCallback(async () => {
    if (isStartingRef.current || isRecording || isProcessing) return;
    isStartingRef.current = true;

    try {
      if (pendingCleanup) {
        await pendingCleanup;
        pendingCleanup = null;
      }

      const { granted } = await Audio.requestPermissionsAsync();
      if (!granted) return;

      setRecordingUri(null);
      await cleanupRecording();

      // Force-reset the audio session: deactivate then reactivate so iOS flushes
      // any session held by the camera (which records video+audio and may not
      // have released it synchronously on unmount).
      await Audio.setAudioModeAsync({ allowsRecordingIOS: false });
      await new Promise(r => setTimeout(r, 200));
      await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });

      let recording: Audio.Recording | null = null;
      for (let attempt = 0; attempt < 5; attempt++) {
        try {
          const rec = new Audio.Recording();
          await rec.prepareToRecordAsync(SPEECH_RECORDING_OPTIONS);
          recording = rec;
          break;
        } catch {
          if (attempt < 4) await new Promise(r => setTimeout(r, 600));
          else throw new Error('Audio session unavailable after 5 attempts');
        }
      }
      if (!recording) return;

      recordingRef.current = recording;
      await recording.startAsync();
      setIsRecording(true);
    } catch (e) {
      await cleanupRecording();
      await Audio.setAudioModeAsync({ allowsRecordingIOS: false }).catch(() => {});
      console.error('useSpeechUpload: start failed', e);
    } finally {
      isStartingRef.current = false;
    }
  }, [cleanupRecording, isProcessing, isRecording]);

  const stop = useCallback(async (): Promise<SpeechResult | null> => {
    const rec = recordingRef.current;
    recordingRef.current = null;
    if (!rec || isStartingRef.current) return null;

    setIsRecording(false);
    setIsProcessing(true);
    try {
      await rec.stopAndUnloadAsync();
      await Audio.setAudioModeAsync({ allowsRecordingIOS: false });
      const uri = rec.getURI();
      recordingRef.current = null;
      if (!uri) return null;
      setRecordingUri(uri);

      const txRes = await transcribeAudio(uri);
      if (!txRes.ok || !txRes.data.transcript) return null;
      const transcript = txRes.data.transcript;

      const glossRes = await getGloss(transcript);
      const gloss = glossRes.ok ? glossRes.data.gloss : '';

      return { transcript, gloss, audioUri: uri };
    } catch (e) {
      console.error('useSpeechUpload: stop/upload failed', e);
      return null;
    } finally {
      setIsProcessing(false);
      setRecordingUri(null);
    }
  }, []);

  return { isRecording, isProcessing, recordingUri, start, stop };
}
