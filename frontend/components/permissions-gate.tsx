import { useCameraPermissions, useMicrophonePermissions } from 'expo-camera';
import * as MediaLibrary from 'expo-media-library';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';

type Props = { children: React.ReactNode };

export function PermissionsGate({ children }: Props) {
  const [cameraPermission, requestCameraPermission] = useCameraPermissions();
  const [micPermission, requestMicPermission] = useMicrophonePermissions();
  const [mediaPermission, requestMediaPermission] = MediaLibrary.usePermissions();

  if (!cameraPermission || !micPermission || !mediaPermission) return <View />;

  const allGranted =
    cameraPermission.granted && micPermission.granted && mediaPermission.granted;

  if (!allGranted) {
    return (
      <View style={styles.container}>
        <TouchableOpacity
          style={styles.grantButton}
          onPress={() => {
            requestCameraPermission();
            requestMicPermission();
            requestMediaPermission();
          }}
        >
          <Text style={styles.buttonText}>Grant Permissions</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return <>{children}</>;
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: 'black' },
  grantButton: { backgroundColor: '#2196F3', padding: 15, margin: 100, borderRadius: 10 },
  buttonText: { color: 'white', textAlign: 'center', fontWeight: 'bold' },
});
