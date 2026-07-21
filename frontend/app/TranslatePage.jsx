import { BottomNav } from '@/components/bottom-nav';
import { CameraRecorder } from '@/components/camera-recorder';
import { HistoryDrawer } from '@/components/history-drawer';
import { VoicePickerModal } from '@/components/voice-picker-modal';
import { useSessionScope } from '@/contexts/SessionContext';
import { useVideoUpload } from '@/hooks/use-video-upload';
import { useSpeechUpload } from '@/hooks/use-speech-upload';
import { getConversationTitle, getSessionId, resetSession, setSessionId } from '@/lib/api';
import { Audio } from 'expo-av';
import { Image as ExpoImage } from 'expo-image';
import * as Speech from 'expo-speech';
import { useVideoPlayer, VideoView } from 'expo-video';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
    ActivityIndicator,
    Animated,
    Image,
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

// Faux waveform pattern for voice-message bubbles — static so it doesn't
// re-shuffle on every render.
const WAVE_HEIGHTS = [6, 10, 14, 8, 18, 12, 22, 16, 10, 20, 14, 8, 12, 6, 18, 10];

// ─── MessageBubble ────────────────────────────────────────────────────────────
// sign_to_text  → left,  primary = ASL gloss,  secondary = English
// speech_to_text → right, primary = transcript, secondary = ASL gloss
function MessageBubble({ message, onSpeakSystem, isSystemSpeaking }) {
    const slide = useRef(new Animated.Value(60)).current;
    const fade = useRef(new Animated.Value(0)).current;

    useEffect(() => {
        Animated.parallel([
            Animated.spring(slide, { toValue: 0, useNativeDriver: true, tension: 60, friction: 12 }),
            Animated.timing(fade, { toValue: 1, duration: 280, useNativeDriver: true }),
        ]).start();
    }, [fade, slide]);

    const isSign = message.type === 'sign_to_text';
    const primary = isSign ? message.gloss : message.transcript;
    const secondary = isSign ? message.english : message.gloss;

    const localVideoUri = isSign ? message.videoUri : null;
    const localAudioUri = !isSign ? message.audioUri : null;

    const videoPlayer = useVideoPlayer(localVideoUri || '', (p) => {
        p.loop = true;
        p.muted = true;
    });
    const [isVideoPlaying, setIsVideoPlaying] = useState(false);
    const toggleVideo = useCallback(() => {
        if (isVideoPlaying) {
            videoPlayer.pause();
            setIsVideoPlaying(false);
        } else {
            videoPlayer.play();
            setIsVideoPlaying(true);
        }
    }, [isVideoPlaying, videoPlayer]);

    const soundRef = useRef(null);
    const [isAudioPlaying, setIsAudioPlaying] = useState(false);
    useEffect(() => {
        return () => {
            soundRef.current?.unloadAsync().catch(() => {});
            soundRef.current = null;
        };
    }, []);
    const toggleAudio = useCallback(async () => {
        try {
            if (isAudioPlaying) {
                await soundRef.current?.pauseAsync();
                setIsAudioPlaying(false);
                return;
            }
            if (!soundRef.current && localAudioUri) {
                const { sound } = await Audio.Sound.createAsync({ uri: localAudioUri });
                soundRef.current = sound;
                sound.setOnPlaybackStatusUpdate((status) => {
                    if (status.didJustFinish) {
                        setIsAudioPlaying(false);
                        sound.setPositionAsync(0).catch(() => {});
                    }
                });
            }
            await soundRef.current?.playAsync();
            setIsAudioPlaying(true);
        } catch (e) {
            console.error('MessageBubble audio playback failed', e);
        }
    }, [isAudioPlaying, localAudioUri]);

    return (
        <Animated.View style={[
            styles.bubbleRow,
            isSign ? styles.rowLeft : styles.rowRight,
            { transform: [{ translateY: slide }], opacity: fade },
        ]}>
            <View style={isSign ? styles.bubbleColumnLeft : styles.bubbleColumnRight}>
                {!!localVideoUri && (
                    <TouchableOpacity activeOpacity={0.85} onPress={toggleVideo} style={styles.recordedVideoWrap}>
                        <VideoView
                            player={videoPlayer}
                            style={styles.recordedVideo}
                            nativeControls={false}
                            contentFit="cover"
                        />
                        {!isVideoPlaying && (
                            <View style={styles.playOverlay} pointerEvents="none">
                                <View style={styles.playCircleSmall}>
                                    <MaterialCommunityIcons name="play" size={20} color="#432818" />
                                </View>
                            </View>
                        )}
                    </TouchableOpacity>
                )}
                {!!localAudioUri && (
                    <TouchableOpacity activeOpacity={0.85} onPress={toggleAudio} style={styles.recordedAudioWrap}>
                        <View style={styles.audioPlayCircle}>
                            <MaterialCommunityIcons
                                name={isAudioPlaying ? 'pause' : 'play'}
                                size={18}
                                color="#FDF0D0"
                            />
                        </View>
                        <View style={styles.audioWaveformWrap}>
                            {WAVE_HEIGHTS.map((h, i) => (
                                <View key={i} style={[styles.audioWaveBar, { height: h }]} />
                            ))}
                        </View>
                    </TouchableOpacity>
                )}
                <TouchableOpacity
                    onPress={onSpeakSystem}
                    disabled={!onSpeakSystem}
                    activeOpacity={onSpeakSystem ? 0.75 : 1}
                    style={[styles.bubble, isSign ? styles.bubbleSign : styles.bubbleSpeech]}
                >
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
                    {isSystemSpeaking && (
                        <View style={styles.speakingRow}>
                            <ActivityIndicator size="small" color={isSign ? '#432818' : 'rgba(253,240,208,0.7)'} />
                        </View>
                    )}
                </TouchableOpacity>
            </View>
        </Animated.View>
    );
}

// ─── PendingBubble ────────────────────────────────────────────────────────────
// Sign flow:   shows the recorded clip with a Messenger-style play button.
// Speech flow: shows the recorded audio as a play/pause voice-message bubble.
// Either flow falls back to a meme GIF if no media URI is available.
function PendingBubble({ isSign, videoUri, audioUri }) {
    const slide = useRef(new Animated.Value(60)).current;
    const fade = useRef(new Animated.Value(0)).current;
    const gifUri = useMemo(
        () => WAITING_GIFS[Math.floor(Math.random() * WAITING_GIFS.length)],
        [],
    );

    const player = useVideoPlayer(videoUri || '', (p) => {
        p.loop = true;
        p.muted = true;
    });
    const [isVideoPlaying, setIsVideoPlaying] = useState(false);

    const soundRef = useRef(null);
    const [isAudioPlaying, setIsAudioPlaying] = useState(false);

    useEffect(() => {
        Animated.parallel([
            Animated.spring(slide, { toValue: 0, useNativeDriver: true, tension: 60, friction: 12 }),
            Animated.timing(fade, { toValue: 1, duration: 280, useNativeDriver: true }),
        ]).start();
    }, [fade, slide]);

    useEffect(() => {
        return () => {
            // Unload audio when the bubble disappears (processing finished or
            // user navigated away). expo-av leaks otherwise.
            soundRef.current?.unloadAsync().catch(() => {});
            soundRef.current = null;
        };
    }, []);

    const toggleVideo = useCallback(() => {
        if (isVideoPlaying) {
            player.pause();
            setIsVideoPlaying(false);
        } else {
            player.play();
            setIsVideoPlaying(true);
        }
    }, [isVideoPlaying, player]);

    const toggleAudio = useCallback(async () => {
        try {
            if (isAudioPlaying) {
                await soundRef.current?.pauseAsync();
                setIsAudioPlaying(false);
                return;
            }
            if (!soundRef.current && audioUri) {
                const { sound } = await Audio.Sound.createAsync({ uri: audioUri });
                soundRef.current = sound;
                sound.setOnPlaybackStatusUpdate((status) => {
                    if (status.didJustFinish) {
                        setIsAudioPlaying(false);
                        sound.setPositionAsync(0).catch(() => {});
                    }
                });
            }
            await soundRef.current?.playAsync();
            setIsAudioPlaying(true);
        } catch (e) {
            console.error('PendingBubble audio playback failed', e);
        }
    }, [isAudioPlaying, audioUri]);

    const showVideo = isSign && !!videoUri;
    const showAudio = !isSign && !!audioUri;

    return (
        <Animated.View style={[
            styles.bubbleRow,
            isSign ? styles.rowLeft : styles.rowRight,
            { transform: [{ translateY: slide }], opacity: fade },
        ]}>
            <View style={[
                styles.bubble,
                isSign ? styles.bubbleSign : styles.bubbleSpeech,
                showAudio ? styles.pendingAudioBubble : styles.pendingBubble,
            ]}>
                {showVideo ? (
                    <TouchableOpacity activeOpacity={0.85} onPress={toggleVideo} style={styles.pendingVideoWrap}>
                        <VideoView
                            player={player}
                            style={styles.pendingVideo}
                            nativeControls={false}
                            contentFit="cover"
                        />
                        {!isVideoPlaying && (
                            <View style={styles.playOverlay} pointerEvents="none">
                                <View style={styles.playCircle}>
                                    <MaterialCommunityIcons name="play" size={28} color="#432818" />
                                </View>
                            </View>
                        )}
                        <View style={styles.processingPill} pointerEvents="none">
                            <ActivityIndicator size="small" color="#fff" />
                            <Text style={styles.processingPillText}>Translating…</Text>
                        </View>
                    </TouchableOpacity>
                ) : showAudio ? (
                    <TouchableOpacity activeOpacity={0.85} onPress={toggleAudio} style={styles.pendingAudioWrap}>
                        <View style={styles.audioPlayCircle}>
                            <MaterialCommunityIcons
                                name={isAudioPlaying ? 'pause' : 'play'}
                                size={20}
                                color="#FDF0D0"
                            />
                        </View>
                        <View style={styles.audioWaveformWrap}>
                            {WAVE_HEIGHTS.map((h, i) => (
                                <View key={i} style={[styles.audioWaveBar, { height: h }]} />
                            ))}
                        </View>
                        <ActivityIndicator size="small" color="rgba(253,240,208,0.8)" />
                    </TouchableOpacity>
                ) : (
                    <ExpoImage
                        source={{ uri: gifUri }}
                        style={styles.pendingGif}
                        contentFit="cover"
                        transition={120}
                    />
                )}
            </View>
        </Animated.View>
    );
}

// ─── TranslatePage ────────────────────────────────────────────────────────────
export default function TranslatePage({ onNavigateTo }) {
    const {
        activeConversation,
        activeConversationId,
        conversations,
        addMessage,
        newConversation,
        selectConversation,
        updateConversation,
        selectedVoice,
    } = useSessionScope('translate');

    const [showRecorder, setShowRecorder] = useState(false);
    const [processingSign, setProcessingSign] = useState(false);
    const [pendingVideoUri, setPendingVideoUri] = useState(null);
    const [systemSpeakingId, setSystemSpeakingId] = useState(null);
    const [drawerOpen, setDrawerOpen] = useState(false);
    const [voicePickerOpen, setVoicePickerOpen] = useState(false);
    const scrollRef = useRef(null);

    const messages = activeConversation?.messages || [];
    const title = activeConversation?.title && activeConversation.title !== 'New conversation'
        ? activeConversation.title
        : 'Translate';

    // Cold-start: if no translate conversation exists yet, spin one up with
    // a fresh backend session id. We do NOT reset on every mount anymore —
    // that would wipe history every time the user navigates away and back.
    useEffect(() => {
        if (!activeConversationId && conversations.length === 0) {
            const sid = resetSession();
            newConversation({ sessionId: sid });
        } else if (activeConversation?.sessionId) {
            // Make sure backend session id matches the active conversation
            // (e.g. after the user picked a different one from the drawer).
            setSessionId(activeConversation.sessionId);
        }
    }, [activeConversationId, conversations.length, activeConversation?.sessionId, newConversation]);

    // Stop any in-flight system speech when switching conversations.
    useEffect(() => {
        Speech.stop();
        setSystemSpeakingId(null);
    }, [activeConversationId]);

    // After a sign/speech turn lands, ask the backend for a 1-3 word topic
    // label and patch the conversation title. Only re-fetch at message
    // counts 1 and 3 so we don't burn Gemini calls on every clip.
    useEffect(() => {
        if (!activeConversationId) return;
        if (messages.length !== 1 && messages.length !== 3) return;
        const sid = getSessionId();
        let cancelled = false;
        (async () => {
            const res = await getConversationTitle(sid);
            if (cancelled) return;
            if (res.ok && res.data.title) {
                updateConversation(activeConversationId, { title: res.data.title });
            }
        })();
        return () => { cancelled = true; };
    }, [messages.length, activeConversationId, updateConversation]);

    const { send: sendVideo } = useVideoUpload();
    const { isRecording, isProcessing: processingMic, recordingUri: pendingAudioUri, start: startMic, stop: stopMic } = useSpeechUpload();

    const scrollToBottom = useCallback(() => {
        setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 80);
    }, []);

    // Scroll down whenever a pending bubble appears
    useEffect(() => {
        if (processingSign || processingMic) scrollToBottom();
    }, [processingSign, processingMic, scrollToBottom]);

    const speakWithSystemVoice = useCallback((id, text) => {
        if (!selectedVoice || !text) return;
        Speech.stop();
        setSystemSpeakingId(id);
        Speech.speak(text, {
            voice: selectedVoice.identifier,
            language: selectedVoice.language,
            onDone: () => setSystemSpeakingId((cur) => (cur === id ? null : cur)),
            onStopped: () => setSystemSpeakingId((cur) => (cur === id ? null : cur)),
            onError: () => setSystemSpeakingId((cur) => (cur === id ? null : cur)),
        });
    }, [selectedVoice]);

    const handleRecorded = async (uri) => {
        setShowRecorder(false);
        setPendingVideoUri(uri);
        setProcessingSign(true);
        const result = await sendVideo(uri);
        setProcessingSign(false);
        setPendingVideoUri(null);
        if (result.kind === 'success') {
            const videoId = result.data.video_id;
            const english = result.data.english?.trim() || '';
            addMessage({
                type: 'sign_to_text',
                gloss: result.data.gloss?.trim() || 'Unknown sign',
                english,
                videoId,
                videoUri: uri,
            });
            scrollToBottom();
        }
    };

    const handleCameraPress = () => {
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
                    audioUri: result.audioUri,        // keep recorded voice memo playable
                });
                scrollToBottom();
            }
        } else {
            await startMic();
        }
    };

    const handleNewConversation = () => {
        Speech.stop();
        const sid = resetSession();
        newConversation({ sessionId: sid });
    };

    const handleSelectConversation = (id) => {
        Speech.stop();
        // The cold-start effect above will call setSessionId once activeConversation updates.
        selectConversation(id);
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
                    <View style={styles.headerLeft}>
                        <TouchableOpacity
                            style={styles.headerIconBtn}
                            onPress={() => setDrawerOpen(true)}
                            hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
                        >
                            <MaterialCommunityIcons name="menu" size={22} color="#2c2c2e" />
                        </TouchableOpacity>
                    </View>
                    <View style={styles.headerCenter}>
                        <Text style={styles.title} numberOfLines={1}>{title}</Text>
                    </View>
                    <View style={styles.headerRight}>
                        <TouchableOpacity
                            style={styles.headerIconBtn}
                            onPress={() => setVoicePickerOpen(true)}
                            hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
                        >
                            <MaterialCommunityIcons name="account-voice" size={20} color="#2c2c2e" />
                        </TouchableOpacity>
                        {!!selectedVoice && (
                            <Text style={styles.voiceLabel} numberOfLines={1}>
                                {selectedVoice.name}
                            </Text>
                        )}
                    </View>
                </View>

                <ScrollView
                    ref={scrollRef}
                    style={styles.list}
                    contentContainerStyle={styles.listContent}
                    showsVerticalScrollIndicator={false}
                >
                    {messages.length === 0 && !processingSign && !processingMic && (
                        <View style={styles.emptyState}>
                            <View style={styles.emptyIconBadge}>
                                <Image
                                    source={require('../assets/images/empty-translate.png')}
                                    style={styles.emptyIcon}
                                    resizeMode="contain"
                                />
                            </View>
                            <Text style={styles.emptyText}>Tap the camera to sign{'\n'}or the mic to speak</Text>
                        </View>
                    )}
                    {messages.map(msg => {
                        const speakText = msg.type === 'sign_to_text'
                            ? (msg.english || msg.gloss)
                            : msg.transcript;
                        const canSpeak = !!selectedVoice && !!speakText;
                        return (
                            <MessageBubble
                                key={msg.id}
                                message={msg}
                                        onSpeakSystem={canSpeak ? () => speakWithSystemVoice(msg.id, speakText) : undefined}
                                isSystemSpeaking={systemSpeakingId === msg.id}
                            />
                        );
                    })}
                    {processingSign && <PendingBubble isSign={true} videoUri={pendingVideoUri} />}
                    {processingMic && <PendingBubble isSign={false} audioUri={pendingAudioUri} />}
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

                <BottomNav active="translate" onNavigateTo={onNavigateTo} />

                <HistoryDrawer
                    visible={drawerOpen}
                    onClose={() => setDrawerOpen(false)}
                    onOpenVoicePicker={() => setVoicePickerOpen(true)}
                    pageType="translate"
                    onSelectConversation={handleSelectConversation}
                    onNewConversation={handleNewConversation}
                />
                <VoicePickerModal
                    visible={voicePickerOpen}
                    onClose={() => setVoicePickerOpen(false)}
                />
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
        paddingHorizontal: 12,
        flexDirection: 'row',
        alignItems: 'center',
    },
    headerIconBtn: {
        width: 40,
        height: 40,
        borderRadius: 20,
        justifyContent: 'center',
        alignItems: 'center',
    },
    headerLeft: {
        width: 110,
        alignItems: 'flex-start',
    },
    headerCenter: { flex: 1, alignItems: 'center' },
    headerRight: {
        alignItems: 'flex-end',
        justifyContent: 'center',
        width: 110,
    },
    title: {
        color: '#2c2c2e',
        fontSize: 22,
        fontWeight: '700',
    },
    voiceLabel: {
        color: '#a09880',
        fontSize: 12,
        textAlign: 'right',
        marginTop: 4,
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
        paddingBottom: 40,           // breathing room above the FABs so the
                                     // first message doesn't sit right on them
        gap: 10,
    },
    bubbleColumnLeft: {
        flexShrink: 1,
        alignItems: 'flex-start',
        maxWidth: '78%',
        gap: 14,
    },
    bubbleColumnRight: {
        flexShrink: 1,
        alignItems: 'flex-end',
        maxWidth: '78%',
        gap: 14,
    },
    speakingRow: {
        marginTop: 6,
        alignItems: 'flex-start',
    },
    reasoningRow: {
        flexDirection: 'row',
        alignItems: 'flex-start',
        gap: 4,
        marginTop: 4,
    },
    reasoningInBubble: {
        fontSize: 10,
        color: '#8b7c69',
        fontStyle: 'italic',
        flexShrink: 1,
        lineHeight: 14,
    },
    reasoningBoldInBubble: {
        fontWeight: '700',
        color: '#432818',
        fontStyle: 'normal',
    },
    recordedVideoWrap: {
        width: 140,
        height: 180,
        borderRadius: 12,
        overflow: 'hidden',
        backgroundColor: '#000',
    },
    recordedVideo: {
        width: '100%',
        height: '100%',
    },
    playCircleSmall: {
        width: 40,
        height: 40,
        borderRadius: 20,
        backgroundColor: 'rgba(255,255,255,0.95)',
        alignItems: 'center',
        justifyContent: 'center',
        paddingLeft: 3,
        shadowColor: '#000',
        shadowOpacity: 0.25,
        shadowRadius: 4,
        shadowOffset: { width: 0, height: 1 },
        elevation: 3,
    },
    recordedAudioWrap: {
        width: 200,
        flexDirection: 'row',
        alignItems: 'center',
        gap: 10,
        paddingVertical: 8,
        paddingHorizontal: 12,
        borderRadius: 18,
        borderBottomRightRadius: 4,
        backgroundColor: '#432818',
    },
    emptyState: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
        paddingBottom: 60,
        gap: 16,
    },
    // Matches the badge on Voice and Animation so all three empty states agree.
    emptyIconBadge: {
        width: 96,
        height: 96,
        borderRadius: 48,
        backgroundColor: '#FDF0D0',
        borderWidth: 1,
        borderColor: '#e0d8cc',
        alignItems: 'center',
        justifyContent: 'center',
        shadowColor: '#432818',
        shadowOpacity: 0.08,
        shadowRadius: 10,
        shadowOffset: { width: 0, height: 4 },
        elevation: 2,
    },
    // tintColor flattens the artwork to exactly the brand brown, so the three
    // empty-state marks stay identical in hue even if the source PNGs drift.
    emptyIcon: {
        width: 48,
        height: 48,
        tintColor: '#432818',
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
        alignItems: 'flex-end',
    },
    rowLeft: {
        justifyContent: 'flex-start',
    },
    rowRight: {
        justifyContent: 'flex-end',
    },

    // ── bubbles ──
    bubble: {
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
    pendingVideoWrap: {
        width: 200,
        height: 260,
        borderRadius: 12,
        overflow: 'hidden',
        backgroundColor: '#000',
    },
    pendingVideo: {
        width: '100%',
        height: '100%',
    },
    playOverlay: {
        ...StyleSheet.absoluteFillObject,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'rgba(0,0,0,0.25)',
    },
    playCircle: {
        width: 56,
        height: 56,
        borderRadius: 28,
        backgroundColor: 'rgba(255,255,255,0.95)',
        alignItems: 'center',
        justifyContent: 'center',
        paddingLeft: 4,
        shadowColor: '#000',
        shadowOpacity: 0.25,
        shadowRadius: 6,
        shadowOffset: { width: 0, height: 2 },
        elevation: 4,
    },
    processingPill: {
        position: 'absolute',
        bottom: 8,
        left: 8,
        right: 8,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        paddingVertical: 6,
        paddingHorizontal: 10,
        backgroundColor: 'rgba(0,0,0,0.55)',
        borderRadius: 12,
        gap: 8,
    },
    processingPillText: {
        color: '#fff',
        fontSize: 12,
        fontWeight: '600',
    },
    pendingAudioBubble: {
        paddingVertical: 10,
        paddingHorizontal: 14,
    },
    pendingAudioWrap: {
        width: 220,
        flexDirection: 'row',
        alignItems: 'center',
        gap: 10,
    },
    audioPlayCircle: {
        width: 36,
        height: 36,
        borderRadius: 18,
        backgroundColor: 'rgba(253,240,208,0.18)',
        alignItems: 'center',
        justifyContent: 'center',
    },
    audioWaveformWrap: {
        flex: 1,
        flexDirection: 'row',
        alignItems: 'center',
        gap: 3,
        height: 24,
    },
    audioWaveBar: {
        width: 3,
        backgroundColor: 'rgba(253,240,208,0.65)',
        borderRadius: 2,
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
});
