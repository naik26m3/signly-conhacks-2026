import { useEffect } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
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
          <TouchableOpacity
            style={styles.cancelButton}
            onPress={() => {
              player.pause();
              onReset();
            }}
          >
            <Text style={styles.buttonText}>Record Again</Text>
          </TouchableOpacity>
        ) : (
          <>
            <TouchableOpacity
              style={styles.cancelButton}
              onPress={() => {
                player.pause();
                onCancel();
              }}
              disabled={upload.kind === 'uploading'}
            >
              <Text style={styles.buttonText}>Cancel</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.saveButton, upload.kind === 'uploading' && styles.disabled]}
              onPress={onSend}
              disabled={upload.kind === 'uploading'}
            >
              <Text style={styles.buttonText}>
                {upload.kind === 'uploading' ? 'Sending…' : 'Send to API'}
              </Text>
            </TouchableOpacity>
          </>
        )}
      </View>
    </View>
  );
}

function ResultPanel({ upload }: { upload: UploadResult }) {
  return (
    <View style={styles.resultPanel}>
      {upload.kind === 'uploading' && (
        <View style={styles.resultRow}>
          <ActivityIndicator color="#fff" />
          <Text style={styles.resultTitle}>  Uploading…</Text>
        </View>
      )}

      {upload.kind === 'success' && (
        <ScrollView style={styles.resultScroll}>
          <Text style={[styles.resultTitle, { color: '#7CFC8A' }]}>
            ✓ Upload OK ({upload.status})
          </Text>
          {upload.data?.video_id && (
            <Text style={styles.resultLine}>video_id: {upload.data.video_id}</Text>
          )}
          {upload.data?.status && (
            <Text style={styles.resultLine}>status: {upload.data.status}</Text>
          )}
          <Text style={styles.resultMono}>{JSON.stringify(upload.data, null, 2)}</Text>
        </ScrollView>
      )}

      {upload.kind === 'error' && (
        <ScrollView style={styles.resultScroll}>
          <Text style={[styles.resultTitle, { color: '#FF6B6B' }]}>
            ✗ Upload failed{upload.status ? ` (${upload.status})` : ''}
          </Text>
          <Text style={styles.resultMono}>{upload.message}</Text>
        </ScrollView>
      )}
    </View>
  );
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
  cancelButton: { backgroundColor: 'rgba(255,0,0,0.7)', padding: 15, borderRadius: 30, width: 120 },
  saveButton: { backgroundColor: 'rgba(0,255,0,0.7)', padding: 15, borderRadius: 30, width: 120 },
  disabled: { opacity: 0.5 },
  resultPanel: {
    position: 'absolute',
    top: 60,
    left: 16,
    right: 16,
    maxHeight: '50%',
    backgroundColor: 'rgba(0,0,0,0.78)',
    borderRadius: 12,
    padding: 14,
  },
  resultRow: { flexDirection: 'row', alignItems: 'center' },
  resultScroll: { maxHeight: 280 },
  resultTitle: { color: 'white', fontSize: 16, fontWeight: 'bold', marginBottom: 6 },
  resultLine: { color: 'white', fontSize: 13, marginBottom: 2 },
  resultMono: {
    color: '#D8E0FF',
    fontSize: 11,
    fontFamily: 'Courier',
    marginTop: 6,
  },
});
