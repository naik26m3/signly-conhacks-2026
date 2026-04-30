import { CameraRecorder } from '@/components/camera-recorder';
import { useVideoUpload } from '@/hooks/use-video-upload';
import { useSpeechUpload } from '@/hooks/use-speech-upload';
import { getAudioUrl } from '@/lib/api';
import { useCameraPermissions, useMicrophonePermissions } from 'expo-camera';
import { Audio } from 'expo-av';
import { Image as ExpoImage } from 'expo-image';
import { MaterialCommunityIcons, MaterialIcons } from '@expo/vector-icons';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
    ActivityIndicator,
    Animated,
    ScrollView,
    StyleSheet,
    Text,
    TouchableOpacity,
    View,
} from 'react-native';

// Waiting meme GIFs — rotated randomly while a sign clip is being processed.
const WAITING_GIFS = [
    'https://media.giphy.com/media/tRrSky6QzB6SmxLHMP/giphy.gif',     // SpongeBob waiting
    'https://media.giphy.com/media/PCvkgunX9ZbEEyfTQH/giphy.gif',     // Skeleton "where you at?"
    'https://media.giphy.com/media/FoH28ucxZFJZu/giphy.gif',          // Titanic "84 years"
    'https://media.giphy.com/media/4NnTap3gOhhlik1YEw/giphy.gif',     // Caddyshack "we're waiting"
    'https://media.giphy.com/media/sthmCnCpfr8M8jtTQy/giphy.gif',     // Bongo Cat
];

// ─── MessageBubble ────────────────────────────────────────────────────────────
// sign_to_text  → left,  primary = ASL gloss,  secondary = English
// speech_to_text → right, primary = transcript, secondary = ASL gloss
function MessageBubble({ message, onPlay }) {
    const slide = useRef(new Animated.Value(32)).current;
    const fade = useRef(new Animated.Value(0)).current;

    useEffect(() => {
        Animated.parallel([
            Animated.spring(slide, { toValue: 0, useNativeDriver: true, tension: 90, friction: 11 }),
            Animated.timing(fade, { toValue: 1, duration: 220, useNativeDriver: true }),
        ]).start();
    }, []);

    const isSign = message.type === 'sign_to_text';
    const primary = isSign ? message.gloss : message.transcript;
    const secondary = isSign ? message.english : message.gloss;

    return (
        <Animated.View style={[
            styles.bubbleRow,
            isSign ? styles.rowLeft : styles.rowRight,
            { transform: [{ translateY: slide }], opacity: fade },
        ]}>
            <View style={[styles.bubble, isSign ? styles.bubbleSign : styles.bubbleSpeech]}>
                <Text style={[styles.primaryText, isSign ? styles.signPrimary : styles.speechPrimary]}>
                    {primary}
                </Text>
                {!!secondary && (
                    <>
                        <View style={[styles.divider, isSign ? styles.signDivider : styles.speechDivider]} />
                        <Text style={[styles.secondaryText, isSign ? styles.signSecondary : styles.speechSecondary]}>
                            {secondary}
                        </Text>
                    </>
                )}
            </View>
            {isSign && !!message.videoId && (
                <TouchableOpacity style={styles.audioBtn} onPress={onPlay} activeOpacity={0.7}>
                    <MaterialCommunityIcons name="volume-high" size={22} color="#432818" />
                </TouchableOpacity>
            )}
        </Animated.View>
    );
}

// ─── PendingBubble ────────────────────────────────────────────────────────────
function PendingBubble({ isSign }) {
    const slide = useRef(new Animated.Value(32)).current;
    const fade = useRef(new Animated.Value(0)).current;
    // Pick a random waiting GIF once per bubble — stays stable across re-renders.
    const gifUri = useMemo(
        () => WAITING_GIFS[Math.floor(Math.random() * WAITING_GIFS.length)],
        [],
    );

    useEffect(() => {
        Animated.parallel([
            Animated.spring(slide, { toValue: 0, useNativeDriver: true, tension: 90, friction: 11 }),
            Animated.timing(fade, { toValue: 1, duration: 220, useNativeDriver: true }),
        ]).start();
    }, []);

    return (
        <Animated.View style={[
            styles.bubbleRow,
            isSign ? styles.rowLeft : styles.rowRight,
            { transform: [{ translateY: slide }], opacity: fade },
        ]}>
            <View style={[styles.bubble, isSign ? styles.bubbleSign : styles.bubbleSpeech, styles.pendingBubble]}>
                <ExpoImage
                    source={{ uri: gifUri }}
                    style={styles.pendingGif}
                    contentFit="cover"
                    transition={120}
                />
            </View>
        </Animated.View>
    );
}

// ─── TranslatePage ────────────────────────────────────────────────────────────
export default function TranslatePage({ onNavigateTo }) {
    const [showRecorder, setShowRecorder] = useState(false);
    const [messages, setMessages] = useState([]);
    const [processingSign, setProcessingSign] = useState(false);
    const scrollRef = useRef(null);

    const [cameraPermission, requestCameraPermission] = useCameraPermissions();
    const [micPermission, requestMicPermission] = useMicrophonePermissions();

    const { send: sendVideo } = useVideoUpload();
    const { isRecording, isProcessing: processingMic, start: startMic, stop: stopMic } = useSpeechUpload();

    const scrollToBottom = useCallback(() => {
        setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 80);
    }, []);

    // Scroll down whenever a pending bubble appears
    useEffect(() => {
        if (processingSign || processingMic) scrollToBottom();
    }, [processingSign, processingMic]);

    const addMessage = useCallback((msg) => {
        setMessages(prev => [...prev, { ...msg, id: String(Date.now()) + String(Math.random()) }]);
        setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 100);
    }, []);

    const playAudio = useCallback(async (videoId) => {
        try {
            const { sound } = await Audio.Sound.createAsync({ uri: getAudioUrl(videoId) });
            await sound.playAsync();
            sound.setOnPlaybackStatusUpdate((status) => {
                if (status.didJustFinish) sound.unloadAsync();
            });
        } catch (e) {
            console.error('playAudio failed', e);
        }
    }, []);

    const handleRecorded = async (uri) => {
        setShowRecorder(false);
        setProcessingSign(true);
        const result = await sendVideo(uri);
        setProcessingSign(false);
        if (result.kind === 'success') {
            const videoId = result.data.video_id;
            const hasAudio = !!result.data.audio_url;
            addMessage({
                type: 'sign_to_text',
                gloss: result.data.gloss?.trim() || 'Unknown sign',
                english: result.data.english?.trim() || '',
                videoId,
                hasAudio,
            });
            playAudio(videoId);
        }
    };

    const handleCameraPress = async () => {
        if (!cameraPermission?.granted) {
            const res = await requestCameraPermission();
            if (!res.granted) return;
        }
        if (!micPermission?.granted) {
            const res = await requestMicPermission();
            if (!res.granted) return;
        }
        setShowRecorder(true);
    };

    const handleMicPress = async () => {
        if (isRecording) {
            const result = await stopMic();
            if (result?.transcript) {
                addMessage({
                    type: 'speech_to_text',
                    transcript: result.transcript,
                    gloss: result.gloss || '',
                });
            }
        } else {
            await startMic();
        }
    };

    if (showRecorder) {
        return (
            <View style={styles.recorderContainer}>
                <CameraRecorder onRecorded={handleRecorded} onCancel={() => setShowRecorder(false)} />
            </View>
        );
    }

    return (
        <View style={styles.screen}>
                <View style={styles.header}>
                    <Text style={styles.title}>Translate</Text>
                </View>

                <ScrollView
                    ref={scrollRef}
                    style={styles.list}
                    contentContainerStyle={styles.listContent}
                    showsVerticalScrollIndicator={false}
                >
                    {messages.length === 0 && !processingSign && !processingMic && (
                        <View style={styles.emptyState}>
                            <Text style={styles.emptyText}>Tap the camera to sign{'\n'}or the mic to speak</Text>
                        </View>
                    )}
                    {messages.map(msg => (
                        <MessageBubble
                            key={msg.id}
                            message={msg}
                            onPlay={msg.videoId ? () => playAudio(msg.videoId) : undefined}
                        />
                    ))}
                    {processingSign && <PendingBubble isSign={true} />}
                    {processingMic && <PendingBubble isSign={false} />}
                </ScrollView>

                <View style={styles.actionRow}>
                    <TouchableOpacity
                        style={[styles.fabCamera, processingSign && styles.fabDisabled]}
                        onPress={handleCameraPress}
                        disabled={processingSign || processingMic}
                    >
                        {processingSign
                            ? <ActivityIndicator size="small" color="#fff" />
                            : <MaterialCommunityIcons name="camera" size={28} color="#ffffff" />
                        }
                    </TouchableOpacity>

                    <TouchableOpacity
                        style={[styles.fabMic, isRecording && styles.fabMicRecording, processingMic && styles.fabDisabled]}
                        onPress={handleMicPress}
                        disabled={processingSign}
                    >
                        {processingMic
                            ? <ActivityIndicator size="small" color="#fff" />
                            : <MaterialCommunityIcons name={isRecording ? 'stop' : 'microphone'} size={24} color="#ffffff" />
                        }
                    </TouchableOpacity>
                </View>

                <View style={styles.navBar}>
                    <View style={[styles.navItem, styles.navItemActive]}>
                        <MaterialIcons name="translate" size={18} color="#FDF0D0" />
                        <Text style={styles.navLabelActive}>Translate</Text>
                    </View>
                    <TouchableOpacity style={styles.navItem} onPress={() => onNavigateTo('animation')}>
                        <MaterialCommunityIcons name="hand-wave" size={18} color="#817f74" />
                        <Text style={styles.navLabelInactive}>Animation</Text>
                    </TouchableOpacity>
                </View>
            </View>
    );
}

const styles = StyleSheet.create({
    screen: {
        flex: 1,
        backgroundColor: '#F9F6F1',
    },
    recorderContainer: {
        ...StyleSheet.absoluteFillObject,
        backgroundColor: '#000',
    },
    header: {
        width: '100%',
        paddingTop: 60,
        paddingBottom: 12,
        alignItems: 'center',
    },
    title: {
        color: '#2c2c2e',
        fontSize: 22,
        fontWeight: '700',
    },

    // ── message list ──
    list: {
        flex: 1,
    },
    listContent: {
        flexGrow: 1,
        justifyContent: 'flex-end',
        paddingHorizontal: 16,
        paddingTop: 12,
        paddingBottom: 8,
        gap: 10,
    },
    emptyState: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
        paddingBottom: 60,
    },
    emptyText: {
        color: '#a09880',
        fontSize: 15,
        textAlign: 'center',
        lineHeight: 24,
    },

    // ── bubble rows ──
    bubbleRow: {
        width: '100%',
        flexDirection: 'row',
        alignItems: 'center',
    },
    audioBtn: {
        marginLeft: 8,
        width: 36,
        height: 36,
        borderRadius: 18,
        backgroundColor: 'rgba(67,40,24,0.10)',
        justifyContent: 'center',
        alignItems: 'center',
    },
    rowLeft: {
        justifyContent: 'flex-start',
    },
    rowRight: {
        justifyContent: 'flex-end',
    },

    // ── bubbles ──
    bubble: {
        maxWidth: '78%',
        borderRadius: 18,
        padding: 14,
        shadowColor: '#000',
        shadowOpacity: 0.07,
        shadowRadius: 8,
        elevation: 3,
    },
    // sign → left, white with brown border
    bubbleSign: {
        backgroundColor: '#ffffff',
        borderWidth: 1,
        borderColor: '#432818',
        borderBottomLeftRadius: 4,
    },
    // speech → right, dark brown
    bubbleSpeech: {
        backgroundColor: '#432818',
        borderBottomRightRadius: 4,
    },
    pendingBubble: {
        padding: 6,
        overflow: 'hidden',
    },
    pendingGif: {
        width: 140,
        height: 100,
        borderRadius: 12,
        backgroundColor: 'rgba(0,0,0,0.05)',
    },

    // ── text ──
    primaryText: {
        fontSize: 20,
        fontWeight: '600',
        lineHeight: 26,
    },
    signPrimary: { color: '#2c2c2e' },
    speechPrimary: { color: '#FDF0D0' },

    divider: {
        height: 1,
        marginVertical: 8,
        borderRadius: 1,
    },
    signDivider: { backgroundColor: '#d4c4b0' },
    speechDivider: { backgroundColor: 'rgba(253,240,208,0.25)' },

    secondaryText: {
        fontSize: 14,
        fontWeight: '300',
        lineHeight: 20,
    },
    signSecondary: { color: '#6b5a48' },
    speechSecondary: { color: 'rgba(253,240,208,0.7)' },

    // ── FABs ──
    actionRow: {
        width: '100%',
        paddingHorizontal: 40,
        flexDirection: 'row',
        justifyContent: 'space-evenly',
        alignItems: 'center',
        marginTop: 8,
        marginBottom: 20,
    },
    fabCamera: {
        width: 70,
        height: 70,
        borderRadius: 35,
        backgroundColor: '#432818',
        justifyContent: 'center',
        alignItems: 'center',
        shadowColor: '#b47e5f',
        shadowOpacity: 1,
        shadowRadius: 8,
        shadowOffset: { width: 0, height: 2 },
        elevation: 8,
    },
    fabMic: {
        width: 70,
        height: 70,
        borderRadius: 35,
        backgroundColor: '#3d2c22',
        justifyContent: 'center',
        alignItems: 'center',
        shadowColor: '#b47e5f',
        shadowOpacity: 1,
        shadowRadius: 8,
        shadowOffset: { width: 0, height: 2 },
        elevation: 6,
    },
    fabMicRecording: {
        backgroundColor: '#c0392b',
        shadowColor: '#e74c3c',
    },
    fabDisabled: {
        opacity: 0.6,
    },

    // ── nav bar ──
    navBar: {
        width: '94%',
        marginBottom: 24,
        alignSelf: 'center',
        backgroundColor: 'rgba(255,255,255,0.55)',
        borderRadius: 50,
        paddingVertical: 12,
        paddingHorizontal: 14,
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        shadowColor: '#000',
        shadowOpacity: 0.08,
        shadowRadius: 18,
        elevation: 6,
    },
    navItem: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
        paddingVertical: 12,
    },
    navItemActive: {
        backgroundColor: 'rgba(100,88,68,0.82)',
        borderRadius: 20,
    },
    navLabelInactive: {
        color: '#817f74',
        fontSize: 12,
        fontWeight: '700',
        marginTop: 6,
    },
    navLabelActive: {
        color: '#FDF0D0',
        fontSize: 12,
        fontWeight: '700',
        marginTop: 6,
    },
});
