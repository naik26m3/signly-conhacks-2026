import { useEffect } from 'react';
import { ActivityIndicator, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { useVideoPlayer, VideoView } from 'expo-video';
import type { UploadResult } from '@/hooks/use-video-upload';

type Props = {
  uri: string;
  upload: UploadResult;
  onSend: () => void;
  onCancel: () => void;
  onReset: () => void;
};

export function VideoPreview({ uri, upload, onSend, onCancel, onReset }: Props) {
  const player = useVideoPlayer(uri, (p) => {
    p.loop = true;
    p.play();
  });

  useEffect(() => {
    if (uri && player) player.play();
  }, [uri, player]);

  const isFinished = upload.kind === 'success' || upload.kind === 'error';

  return (
    <View style={styles.container}>
      <VideoView style={styles.player} player={player} />

      {upload.kind !== 'idle' && <ResultPanel upload={upload} />}

      <View style={styles.actions}>
        {isFinished ? (
          <TouchableOpacity style={styles.cancelButton} onPress={() => { player.pause(); onReset(); }}>
            <Text style={styles.buttonText}>Record Again</Text>
          </TouchableOpacity>
        ) : (
          <>
            <TouchableOpacity
              style={styles.cancelButton}
              onPress={() => { player.pause(); onCancel(); }}
              disabled={upload.kind === 'uploading' || upload.kind === 'processing'}
            >
              <Text style={styles.buttonText}>Cancel</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.sendButton, (upload.kind === 'uploading' || upload.kind === 'processing') && styles.disabled]}
              onPress={onSend}
              disabled={upload.kind === 'uploading' || upload.kind === 'processing'}
            >
              <Text style={styles.buttonText}>
                {upload.kind === 'uploading' ? 'Uploading…' : 'Recognise Sign'}
              </Text>
            </TouchableOpacity>
          </>
        )}
      </View>
    </View>
  );
}

function ResultPanel({ upload }: { upload: UploadResult }) {
  if (upload.kind === 'uploading') {
    return (
      <View style={styles.panel}>
        <ActivityIndicator color="#fff" size="large" />
        <Text style={styles.label}>Uploading video…</Text>
      </View>
    );
  }

  if (upload.kind === 'processing') {
    return (
      <View style={styles.panel}>
        <ActivityIndicator color="#fff" size="large" />
        <Text style={styles.label}>Analysing sign…</Text>
      </View>
    );
  }

  if (upload.kind === 'success') {
    const { gloss, english, confidence, landmarks_found } = upload.data;
    const pct = confidence == null ? null : Math.round(confidence * 100);
    return (
      <View style={styles.panel}>
        <Text style={styles.gloss}>{gloss}</Text>
        {english ? <Text style={styles.english}>{english}</Text> : null}
        <Text style={styles.meta}>
          {pct}% confidence{!landmarks_found ? ' · no landmarks detected' : ''}
        </Text>
      </View>
    );
  }

  if (upload.kind === 'error') {
    return (
      <View style={[styles.panel, styles.errorPanel]}>
        <Text style={styles.errorTitle}>Recognition failed</Text>
        <Text style={styles.errorBody}>{upload.message}</Text>
      </View>
    );
  }

  return null;
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: 'black' },
  player: { flex: 1 },
  actions: {
    position: 'absolute',
    bottom: 50,
    flexDirection: 'row',
    width: '100%',
    justifyContent: 'space-evenly',
  },
  buttonText: { color: 'white', textAlign: 'center', fontWeight: 'bold' },
  cancelButton: { backgroundColor: 'rgba(255,0,0,0.7)', padding: 15, borderRadius: 30, width: 130 },
  sendButton:   { backgroundColor: 'rgba(0,180,80,0.85)', padding: 15, borderRadius: 30, width: 150 },
  disabled: { opacity: 0.5 },

  panel: {
    position: 'absolute',
    top: 60,
    left: 16,
    right: 16,
    backgroundColor: 'rgba(0,0,0,0.82)',
    borderRadius: 16,
    padding: 20,
    alignItems: 'center',
  },
  label:    { color: '#ccc', marginTop: 10, fontSize: 14 },
  gloss:    { color: '#7CFC8A', fontSize: 42, fontWeight: 'bold', letterSpacing: 2 },
  english:  { color: 'white', fontSize: 22, marginTop: 6 },
  meta:     { color: '#aaa', fontSize: 12, marginTop: 8 },

  errorPanel: { borderWidth: 1, borderColor: '#FF6B6B' },
  errorTitle: { color: '#FF6B6B', fontSize: 16, fontWeight: 'bold' },
  errorBody:  { color: '#eee', fontSize: 12, marginTop: 6, textAlign: 'center' },
});
