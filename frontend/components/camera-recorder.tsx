import { Ionicons } from '@expo/vector-icons';
import { CameraView } from 'expo-camera';
import { useVideoPlayer, VideoView } from 'expo-video';
import { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Alert, StyleSheet, Text, TouchableOpacity, View } from 'react-native';

import { detectHands } from '@/lib/api';

type Props = {
  onRecorded: (uri: string) => void;
  onCancel: () => void;
};

type HandsCheck = 'idle' | 'checking' | 'detected' | 'missing' | 'error';

const MAX_RECORD_SECONDS = 10;

export function CameraRecorder({ onRecorded, onCancel }: Props) {
  const [isRecording, setIsRecording] = useState(false);
  const [isCameraReady, setIsCameraReady] = useState(false);
  const [previewUri, setPreviewUri] = useState<string | null>(null);
  const [flashOn, setFlashOn] = useState(false);
  const [facing, setFacing] = useState<'front' | 'back'>('front');
  const [handsCheck, setHandsCheck] = useState<HandsCheck>('idle');
  const [secondsLeft, setSecondsLeft] = useState(MAX_RECORD_SECONDS);
  const cameraRef = useRef<CameraView | null>(null);
  const cameraReadyRef = useRef(false);
  const cameraReadyResolverRef = useRef<(() => void) | null>(null);
  const previewPlayer = useVideoPlayer(previewUri ?? '', (player) => {
    player.loop = true;
  });

  useEffect(() => {
    console.log('Camera facing changed to:', facing);
  }, [facing]);

  useEffect(() => {
    console.log('Flash setting changed to:', flashOn);
  }, [flashOn]);

  useEffect(() => {
    if (previewUri) {
      previewPlayer.play();
    } else {
      previewPlayer.pause();
    }
  }, [previewPlayer, previewUri]);

  useEffect(() => {
    if (!isRecording) {
      setSecondsLeft(MAX_RECORD_SECONDS);
      return;
    }
    setSecondsLeft(MAX_RECORD_SECONDS);
    const interval = setInterval(() => {
      setSecondsLeft((s) => Math.max(0, s - 1));
    }, 1000);
    return () => clearInterval(interval);
  }, [isRecording]);

  useEffect(() => {
    if (!previewUri) {
      setHandsCheck('idle');
      return;
    }
    let cancelled = false;
    setHandsCheck('checking');
    (async () => {
      const result = await detectHands(previewUri);
      if (cancelled) return;
      if (!result.ok) {
        setHandsCheck('error');
        return;
      }
      setHandsCheck(result.data.hands_detected ? 'detected' : 'missing');
    })();
    return () => {
      cancelled = true;
    };
  }, [previewUri]);

  const markCameraReady = () => {
    console.log('Camera is ready');
    cameraReadyRef.current = true;
    setIsCameraReady(true);
    cameraReadyResolverRef.current?.();
    cameraReadyResolverRef.current = null;
  };

  const waitForCameraReady = (timeoutMs = 2500) =>
    new Promise<void>((resolve, reject) => {
      if (cameraReadyRef.current) {
        resolve();
        return;
      }

      const timeout = setTimeout(() => {
        if (cameraReadyResolverRef.current) {
          cameraReadyResolverRef.current = null;
        }
        reject(new Error("Camera didn't become ready in time"));
      }, timeoutMs);

      cameraReadyResolverRef.current = () => {
        clearTimeout(timeout);
        resolve();
      };
    });

  const handleRecord = async () => {
    if (!cameraRef.current) {
      console.log('Camera ref not available');
      Alert.alert('Error', 'Camera not available');
      return;
    }

    if (!cameraReadyRef.current) {
      try {
        await waitForCameraReady();
      } catch {
        Alert.alert('Camera not ready', 'Please wait a moment and try again.');
        return;
      }
    }

    if (isRecording) {
      setIsRecording(false);
      try {
        await cameraRef.current.stopRecording();
      } catch (e) {
        console.error('Stop recording error:', e);
      }
      return;
    }

    setIsRecording(true);

    try {
      console.log('Starting recording...');
      const video = await cameraRef.current.recordAsync({ maxDuration: MAX_RECORD_SECONDS });
      if (video?.uri) {
        console.log('Video recorded:', video.uri);
        setPreviewUri(video.uri);
      }
    } catch (e) {
      console.error('Recording error:', e);
      const errorMessage = e instanceof Error ? e.message : 'Failed to record video';
      Alert.alert('Recording Error', errorMessage);
    } finally {
      setIsRecording(false);
    }
  };

  const handleFlipCamera = () => {
    const newFacing = facing === 'front' ? 'back' : 'front';
    console.log('Flipping camera from', facing, 'to', newFacing);
    if (newFacing === 'front' && flashOn) {
      setFlashOn(false);
    }
    setFacing(newFacing);
  };

  const handleFlashToggle = () => {
    const newFlashState = !flashOn;
    console.log('Toggling flash from', flashOn, 'to', newFlashState);
    setFlashOn(newFlashState);
  };

  const handleCancel = () => {
    onCancel();
  };

  const handlePreviewCancel = () => {
    previewPlayer.pause();
    setPreviewUri(null);
  };

  const handleUseVideo = () => {
    if (!previewUri) return;
    previewPlayer.pause();
    onRecorded(previewUri);
  };

  if (previewUri) {
    return (
      <View style={styles.previewContainer}>
        <VideoView style={styles.previewVideo} player={previewPlayer} nativeControls={false} />
        <TouchableOpacity
          style={[styles.controlButton, styles.previewCancelButton]}
          onPress={handlePreviewCancel}
          activeOpacity={0.8}
        >
          <Ionicons name="close" size={24} color="#ffffff" />
        </TouchableOpacity>
        <View style={[styles.handsBadge, badgeBackgroundFor(handsCheck)]}>
          {handsCheck === 'checking' ? (
            <ActivityIndicator size="small" color="#ffffff" />
          ) : (
            <Ionicons name={badgeIconFor(handsCheck)} size={16} color="#ffffff" />
          )}
          <Text style={styles.handsBadgeText}>{badgeLabelFor(handsCheck)}</Text>
        </View>
        <TouchableOpacity
          style={[styles.previewFloatingButton, styles.previewDownloadButton]}
          onPress={handleUseVideo}
          activeOpacity={0.8}
        >
          <Ionicons name="checkmark" size={24} color="#ffffff" />
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <CameraView
      style={styles.camera}
      ref={cameraRef}
      mode="video"
      facing={facing}
      enableTorch={flashOn}
      zoom={0.0}
      onCameraReady={markCameraReady}
      onMountError={(error) => {
        console.error('Camera mount error:', error);
        Alert.alert('Camera Error', 'Failed to initialize camera');
      }}
    >
      {/* Top Controls */}
      <View style={styles.topControls}>
        {/* Cancel Button */}
        <TouchableOpacity
          style={styles.controlButton}
          onPress={handleCancel}
          activeOpacity={0.6}
        >
          <Ionicons name="close" size={24} color="#ffffff" />
        </TouchableOpacity>

        {/* Flash Toggle (back camera only) */}
        {facing === 'back' ? (
          <TouchableOpacity
            style={[styles.controlButton, flashOn && styles.controlButtonActive]}
            onPress={handleFlashToggle}
            activeOpacity={0.6}
          >
            <Ionicons
              name={flashOn ? 'flash' : 'flash-off'}
              size={24}
              color={flashOn ? '#000000' : '#ffffff'}
            />
          </TouchableOpacity>
        ) : (
          <View style={styles.controlButtonPlaceholder} />
        )}
      </View>

      {/* Recording Countdown */}
      {isRecording && (
        <View style={styles.countdownContainer} pointerEvents="none">
          <View style={[styles.countdownPill, secondsLeft <= 3 && styles.countdownPillUrgent]}>
            <View style={styles.recordDot} />
            <Text style={styles.countdownText}>{secondsLeft}s</Text>
          </View>
          <View style={styles.progressBarTrack}>
            <View
              style={[
                styles.progressBarFill,
                { width: `${(secondsLeft / MAX_RECORD_SECONDS) * 100}%` },
                secondsLeft <= 3 && styles.progressBarFillUrgent,
              ]}
            />
          </View>
        </View>
      )}

      {/* Bottom Controls */}
      <View style={styles.bottomControls}>
        {/* Record/Stop Button */}
        <TouchableOpacity
          style={[styles.recordButton, isRecording && styles.recordButtonRecording]}
          onPress={() => handleRecord()}
          disabled={!isCameraReady}
          activeOpacity={0.8}
        >
          <View style={isRecording ? styles.stopIcon : styles.recordIcon} />
        </TouchableOpacity>

        {/* Flip Camera Button */}
        <TouchableOpacity
          style={[styles.controlButton, styles.flipButton]}
          onPress={handleFlipCamera}
          activeOpacity={0.6}
        >
          <Ionicons name="camera-reverse" size={24} color="#ffffff" />
        </TouchableOpacity>
      </View>
    </CameraView>
  );
}

function badgeLabelFor(state: HandsCheck): string {
  switch (state) {
    case 'checking': return 'Checking for hands…';
    case 'detected': return 'Hands detected';
    case 'missing': return 'No hands found — retake?';
    case 'error': return 'Check failed';
    default: return '';
  }
}

function badgeIconFor(state: HandsCheck): keyof typeof Ionicons.glyphMap {
  switch (state) {
    case 'detected': return 'checkmark-circle';
    case 'missing': return 'warning';
    case 'error': return 'alert-circle';
    default: return 'ellipsis-horizontal';
  }
}

function badgeBackgroundFor(state: HandsCheck) {
  switch (state) {
    case 'detected': return { backgroundColor: 'rgba(34, 139, 75, 0.92)' };
    case 'missing': return { backgroundColor: 'rgba(196, 130, 30, 0.92)' };
    case 'error': return { backgroundColor: 'rgba(150, 60, 60, 0.92)' };
    default: return { backgroundColor: 'rgba(0, 0, 0, 0.55)' };
  }
}

const styles = StyleSheet.create({
  previewContainer: {
    flex: 1,
    backgroundColor: '#000',
  },
  previewVideo: {
    flex: 1,
  },
  previewFloatingButton: {
    position: 'absolute',
    width: 52,
    height: 52,
    borderRadius: 26,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.18)',
  },
  previewCancelButton: {
    top: 60,
    left: 28,
    position: 'absolute',
  },
  previewDownloadButton: {
    bottom: 52,
    right: 26,
  },
  handsBadge: {
    position: 'absolute',
    top: 60,
    alignSelf: 'center',
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    gap: 8,
  },
  handsBadgeText: {
    color: '#ffffff',
    fontSize: 13,
    fontWeight: '600',
  },
  countdownContainer: {
    position: 'absolute',
    top: 120,
    alignSelf: 'center',
    alignItems: 'center',
    gap: 10,
  },
  countdownPill: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: 'rgba(0, 0, 0, 0.55)',
    gap: 8,
  },
  countdownPillUrgent: {
    backgroundColor: 'rgba(196, 60, 60, 0.92)',
  },
  recordDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: '#ff3b30',
  },
  countdownText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '700',
    fontVariant: ['tabular-nums'],
  },
  progressBarTrack: {
    width: 220,
    height: 4,
    borderRadius: 2,
    backgroundColor: 'rgba(255, 255, 255, 0.25)',
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    backgroundColor: '#ffffff',
    borderRadius: 2,
  },
  progressBarFillUrgent: {
    backgroundColor: '#ff3b30',
  },
  camera: {
    flex: 1,
  },
  topControls: {
    position: 'absolute',
    top: 60,
    left: 0,
    right: 0,
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 28,
    zIndex: 10,
  },
  bottomControls: {
    position: 'absolute',
    bottom: 52,
    left: 0,
    right: 0,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 10,
  },
  controlButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.12)',
  },
  controlButtonActive: {
    backgroundColor: 'rgba(255, 255, 255, 0.92)',
  },
  controlButtonPlaceholder: {
    width: 40,
    height: 40,
  },
  recordButton: {
    width: 70,
    height: 70,
    borderRadius: 35,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#432818',
    shadowColor: 'rgba(67, 40, 24, 0.4)',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 1,
    shadowRadius: 20,
    elevation: 8,
  },
  recordButtonRecording: {
    backgroundColor: '#6B4423',
  },
  recordIcon: {
    width: 20,
    height: 20,
    borderRadius: 14,
    backgroundColor: '#ffffff',
  },
  stopIcon: {
    width: 18,
    height: 18,
    backgroundColor: '#ffffff',
    borderRadius: 2,
  },
  flipButton: {
    position: 'absolute',
    right: 40,
  },
});
