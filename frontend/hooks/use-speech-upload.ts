import { transcribeAudio, getGloss } from '@/lib/api';
import { Audio } from 'expo-av';
import { useCallback, useRef, useState } from 'react';

export type SpeechResult = { transcript: string; gloss: string };

export function useSpeechUpload() {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const recordingRef = useRef<Audio.Recording | null>(null);

  const start = useCallback(async () => {
    try {
      const { granted } = await Audio.requestPermissionsAsync();
      if (!granted) return;
      await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
      const { recording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY,
      );
      recordingRef.current = recording;
      setIsRecording(true);
    } catch (e) {
      console.error('useSpeechUpload: start failed', e);
    }
  }, []);

  const stop = useCallback(async (): Promise<SpeechResult | null> => {
    const rec = recordingRef.current;
    if (!rec) return null;

    setIsRecording(false);
    setIsProcessing(true);
    try {
      await rec.stopAndUnloadAsync();
      await Audio.setAudioModeAsync({ allowsRecordingIOS: false });
      const uri = rec.getURI();
      recordingRef.current = null;
      if (!uri) return null;

      const txRes = await transcribeAudio(uri);
      if (!txRes.ok || !txRes.data.transcript) return null;
      const transcript = txRes.data.transcript;

      const glossRes = await getGloss(transcript);
      const gloss = glossRes.ok ? glossRes.data.gloss : '';

      return { transcript, gloss };
    } catch (e) {
      console.error('useSpeechUpload: stop/upload failed', e);
      return null;
    } finally {
      setIsProcessing(false);
    }
  }, []);

  return { isRecording, isProcessing, start, stop };
}
