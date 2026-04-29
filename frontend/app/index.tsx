import { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { Stack } from 'expo-router';

import { CameraRecorder } from '@/components/camera-recorder';
import { PermissionsGate } from '@/components/permissions-gate';
import { VideoPreview } from '@/components/video-preview';
import { useVideoUpload } from '@/hooks/use-video-upload';

export default function App() {
  const [videoUri, setVideoUri] = useState<string | null>(null);
  const { upload, send, reset } = useVideoUpload();

  const handleReset = () => {
    reset();
    setVideoUri(null);
  };

  return (
    <PermissionsGate>
      <View style={styles.container}>
        <Stack.Screen options={{ headerShown: false }} />
        {videoUri ? (
          <VideoPreview
            uri={videoUri}
            upload={upload}
            onSend={() => send(videoUri)}
            onCancel={handleReset}
            onReset={handleReset}
          />
        ) : (
          <CameraRecorder onRecorded={setVideoUri} />
        )}
      </View>
    </PermissionsGate>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: 'black' },
});
