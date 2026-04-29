import { CameraView } from 'expo-camera';
import { useRef, useState } from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';

type Props = { onRecorded: (uri: string) => void };

export function CameraRecorder({ onRecorded }: Props) {
  const [isRecording, setIsRecording] = useState(false);
  const cameraRef = useRef<CameraView>(null);

  const handleRecord = async () => {
    if (!cameraRef.current) return;

    if (isRecording) {
      setIsRecording(false);
      await cameraRef.current.stopRecording();
      return;
    }

    setIsRecording(true);
    try {
      const video = await cameraRef.current.recordAsync();
      if (video?.uri) onRecorded(video.uri);
    } catch (e) {
      console.error('Recording error:', e);
    } finally {
      setIsRecording(false);
    }
  };

  return (
    <CameraView style={styles.camera} ref={cameraRef} mode="video" facing="front">
      <View style={styles.overlay}>
        <TouchableOpacity
          style={[styles.recordButton, isRecording && styles.recordingActive]}
          onPress={handleRecord}
        >
          <View style={isRecording ? styles.stopSquare : styles.recordCircle} />
        </TouchableOpacity>
        <Text style={styles.statusText}>{isRecording ? 'RECORDING...' : 'READY'}</Text>
      </View>
    </CameraView>
  );
}

const styles = StyleSheet.create({
  camera: { flex: 1 },
  overlay: { flex: 1, justifyContent: 'flex-end', alignItems: 'center', paddingBottom: 50 },
  recordButton: {
    width: 80,
    height: 80,
    borderRadius: 40,
    borderWidth: 6,
    borderColor: 'white',
    justifyContent: 'center',
    alignItems: 'center',
  },
  recordingActive: { borderColor: 'red' },
  recordCircle: { width: 50, height: 50, borderRadius: 25, backgroundColor: 'red' },
  stopSquare: { width: 30, height: 30, backgroundColor: 'red', borderRadius: 4 },
  statusText: { color: 'white', marginTop: 15, fontWeight: 'bold' },
});
