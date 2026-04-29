import { CameraView, useCameraPermissions, useMicrophonePermissions } from 'expo-camera';
import * as MediaLibrary from 'expo-media-library';
import { useState, useRef, useEffect } from 'react'; // Added useEffect here
import { StyleSheet, Text, TouchableOpacity, View, Alert } from 'react-native';
import { Stack } from 'expo-router';
import { useVideoPlayer, VideoView } from 'expo-video';

export default function App() {
  const [cameraPermission, requestCameraPermission] = useCameraPermissions();
  const [micPermission, requestMicPermission] = useMicrophonePermissions();
  const [mediaPermission, requestMediaPermission] = MediaLibrary.usePermissions();

  const [isRecording, setIsRecording] = useState(false);
  const [videoUri, setVideoUri] = useState<string | null>(null);
  const cameraRef = useRef<CameraView>(null);

  // 1. Initialize Player
  const player = useVideoPlayer(videoUri, (player) => {
    player.loop = true;
    player.play();
  });

  // 2. Force Autoplay when videoUri is set
  useEffect(() => {
    if (videoUri && player) {
      player.play();
    }
  }, [videoUri, player]);

  // 3. Handle Recording 
  const handleRecord = async () => {
    if (cameraRef.current) {
      if (isRecording) {
        setIsRecording(false);
        await cameraRef.current.stopRecording();
      } else {
        setIsRecording(true);
        try {
          const video = await cameraRef.current.recordAsync();
          if (video?.uri) {
            setVideoUri(video.uri);
          }
        } catch (e) {
          console.error("Recording error:", e);
        } finally {
          setIsRecording(false);
        }
      }
    }
  };

  const sendVideo = async () => {
    if (!videoUri) return;

    // 1. Create the Form Data
    const formData = new FormData();

    // We have to cast this as 'any' because TypeScript can be picky 
    // about the 'uri' property in FormData on React Native
    formData.append('video', {
      uri: videoUri,
      type: 'video/mp4', // Ensure this matches your recording format
      name: 'upload.mp4',
    } as any);

    try {
      const response = await fetch('https://webhook.site/5d5ab75b-1123-4fa8-882a-8ff6acc02607', {
        method: 'POST',
        body: formData,
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      if (response.ok) {
        Alert.alert("Sent!", "The video was uploaded successfully.");
        setVideoUri(null); // Go back to camera
      } else {
        Alert.alert("Upload Failed", "Status: " + response.status);
      }
    } catch (error) {
      console.error("Upload error:", error);
      Alert.alert("Error", "Could not connect to the server.");
    }
  };

  // Permission Check Logic
  if (!cameraPermission || !micPermission || !mediaPermission) return <View />;
  if (!cameraPermission.granted || !micPermission.granted || !mediaPermission.granted) {
    return (
      <View style={styles.container}>
        <TouchableOpacity style={styles.grantButton} onPress={() => {
          requestCameraPermission(); requestMicPermission(); requestMediaPermission();
        }}>
          <Text style={styles.buttonText}>Grant Permissions</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Stack.Screen options={{ headerShown: false }} />

      {videoUri ? (
        /* PREVIEW MODE */
        <View style={styles.container}>
          <VideoView style={styles.camera} player={player} />
          <View style={styles.previewOverlay}>
            <TouchableOpacity
              style={styles.cancelButton}
              onPress={() => {
                player.pause();
                setVideoUri(null);
              }}
            >
              <Text style={styles.buttonText}>Cancel</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.saveButton} onPress={sendVideo}>
              <Text style={styles.buttonText}>Send to API</Text>
            </TouchableOpacity>
          </View>
        </View>
      ) : (
        /* RECORDING MODE */
        <CameraView style={styles.camera} ref={cameraRef} mode="video" facing="front">
          <View style={styles.overlay}>
            <TouchableOpacity
              style={[styles.recordButton, isRecording && styles.recordingActive]}
              onPress={handleRecord}
            >
              <View style={isRecording ? styles.stopSquare : styles.recordCircle} />
            </TouchableOpacity>
            <Text style={styles.statusText}>{isRecording ? "RECORDING..." : "READY"}</Text>
          </View>
        </CameraView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: 'black' },
  camera: { flex: 1 },
  grantButton: { backgroundColor: '#2196F3', padding: 15, margin: 100, borderRadius: 10 },
  buttonText: { color: 'white', textAlign: 'center', fontWeight: 'bold' },
  overlay: { flex: 1, justifyContent: 'flex-end', alignItems: 'center', paddingBottom: 50 },
  previewOverlay: {
    position: 'absolute',
    bottom: 50,
    flexDirection: 'row',
    width: '100%',
    justifyContent: 'space-evenly',
  },
  recordButton: { width: 80, height: 80, borderRadius: 40, borderWidth: 6, borderColor: 'white', justifyContent: 'center', alignItems: 'center' },
  recordingActive: { borderColor: 'red' },
  recordCircle: { width: 50, height: 50, borderRadius: 25, backgroundColor: 'red' },
  stopSquare: { width: 30, height: 30, backgroundColor: 'red', borderRadius: 4 },
  statusText: { color: 'white', marginTop: 15, fontWeight: 'bold' },
  cancelButton: { backgroundColor: 'rgba(255,0,0,0.7)', padding: 15, borderRadius: 30, width: 120 },
  saveButton: { backgroundColor: 'rgba(0,255,0,0.7)', padding: 15, borderRadius: 30, width: 120 },
});