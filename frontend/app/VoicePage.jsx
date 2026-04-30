import { HistoryDrawer } from '@/components/history-drawer';
import { VoicePickerModal } from '@/components/voice-picker-modal';
import { useSessionScope } from '@/contexts/SessionContext';
import { designVoice } from '@/lib/api';
import { MaterialCommunityIcons, MaterialIcons } from '@expo/vector-icons';
import { Audio } from 'expo-av';
import { useCallback, useEffect, useRef, useState } from 'react';
import {
    ActivityIndicator,
    Animated,
    Image,
    KeyboardAvoidingView,
    Platform,
    ScrollView,
    StyleSheet,
    Text,
    TextInput,
    TouchableOpacity,
    View,
} from 'react-native';

const PENDING_PHASES = [
    'Gemini is crafting your voice persona',
    'Composing vocal traits and accent',
    'Sending parameters to ElevenLabs',
    'Generating your custom voice audio',
];

// Bubble wrapping a generated voice. Tapping the play icon replays the sample.
function VoiceBubble({ message, onPlay, isPlaying, onSpeakWithSystem, isSystemSpeaking, systemVoiceLabel }) {
    const slide = useRef(new Animated.Value(32)).current;
    const fade = useRef(new Animated.Value(0)).current;

    useEffect(() => {
        Animated.parallel([
            Animated.spring(slide, { toValue: 0, useNativeDriver: true, tension: 90, friction: 11 }),
            Animated.timing(fade, { toValue: 1, duration: 220, useNativeDriver: true }),
        ]).start();
    }, [fade, slide]);

    return (
        <Animated.View style={[
            styles.bubbleRow,
            styles.rowLeft,
            { transform: [{ translateY: slide }], opacity: fade },
        ]}>
            <View style={[styles.bubble, styles.bubbleVoice]}>
                <View style={styles.voiceHeader}>
                    <MaterialCommunityIcons name="account-voice" size={18} color="#432818" />
                    <Text style={styles.voiceTitle}>{message.params.display_label}</Text>
                </View>

                {message.params.tags?.length > 0 && (
                    <View style={styles.tagsRow}>
                        {message.params.tags.map((t) => <Tag key={t} label={t} />)}
                    </View>
                )}

                <Text style={styles.voiceDescription} numberOfLines={3}>
                    {message.params.voice_description}
                </Text>

                <Text style={styles.sampleText} numberOfLines={4}>
                    “{message.sampleText}”
                </Text>

                <View style={styles.voiceActions}>
                    <TouchableOpacity style={styles.playBtn} onPress={onPlay} activeOpacity={0.7}>
                        {isPlaying
                            ? <ActivityIndicator size="small" color="#FDF0D0" />
                            : <MaterialCommunityIcons name="play" size={18} color="#FDF0D0" />}
                        <Text style={styles.playBtnText}>{isPlaying ? 'Playing…' : 'AI voice'}</Text>
                    </TouchableOpacity>

                    {!!onSpeakWithSystem && (
                        <TouchableOpacity
                            style={styles.systemPlayBtn}
                            onPress={onSpeakWithSystem}
                            activeOpacity={0.7}
                        >
                            {isSystemSpeaking
                                ? <ActivityIndicator size="small" color="#432818" />
                                : <MaterialCommunityIcons name="volume-high" size={16} color="#432818" />}
                            <Text style={styles.systemPlayBtnText} numberOfLines={1}>
                                {systemVoiceLabel || 'System voice'}
                            </Text>
                        </TouchableOpacity>
                    )}
                </View>
            </View>
        </Animated.View>
    );
}

function Tag({ label }) {
    return (
        <View style={styles.tag}>
            <Text style={styles.tagText}>{label}</Text>
        </View>
    );
}

// Right-side bubble for what the user typed.
function UserBubble({ text, onSpeak, isSpeaking, systemVoiceLabel }) {
    const slide = useRef(new Animated.Value(32)).current;
    const fade = useRef(new Animated.Value(0)).current;

    useEffect(() => {
        Animated.parallel([
            Animated.spring(slide, { toValue: 0, useNativeDriver: true, tension: 90, friction: 11 }),
            Animated.timing(fade, { toValue: 1, duration: 220, useNativeDriver: true }),
        ]).start();
    }, [fade, slide]);

    return (
        <Animated.View style={[
            styles.bubbleRow,
            styles.rowRight,
            { transform: [{ translateY: slide }], opacity: fade },
        ]}>
            <View style={styles.userColumn}>
                <View style={[styles.bubble, styles.bubbleUser]}>
                    <Text style={styles.userText}>{text}</Text>
                </View>
                {!!onSpeak && (
                    <TouchableOpacity
                        style={styles.userSpeakBtn}
                        onPress={onSpeak}
                        activeOpacity={0.7}
                    >
                        {isSpeaking
                            ? <ActivityIndicator size="small" color="#432818" />
                            : <MaterialCommunityIcons name="volume-high" size={14} color="#432818" />}
                        <Text style={styles.userSpeakBtnText} numberOfLines={1}>
                            {systemVoiceLabel || 'Read aloud'}
                        </Text>
                    </TouchableOpacity>
                )}
            </View>
        </Animated.View>
    );
}

function PendingBubble() {
    const slide = useRef(new Animated.Value(32)).current;
    const fade = useRef(new Animated.Value(0)).current;
    const [phaseIndex, setPhaseIndex] = useState(0);
    const [dots, setDots] = useState('');

    useEffect(() => {
        Animated.parallel([
            Animated.spring(slide, { toValue: 0, useNativeDriver: true, tension: 90, friction: 11 }),
            Animated.timing(fade, { toValue: 1, duration: 220, useNativeDriver: true }),
        ]).start();
    }, [fade, slide]);

    useEffect(() => {
        const dotsTimer = setInterval(() => {
            setDots(d => d.length >= 3 ? '' : d + '.');
        }, 400);
        const phaseTimer = setInterval(() => {
            setPhaseIndex(i => Math.min(i + 1, PENDING_PHASES.length - 1));
        }, 3500);
        return () => { clearInterval(dotsTimer); clearInterval(phaseTimer); };
    }, []);

    return (
        <Animated.View style={[
            styles.bubbleRow, styles.rowLeft,
            { transform: [{ translateY: slide }], opacity: fade },
        ]}>
            <View style={[styles.bubble, styles.bubbleVoice, styles.pendingBubble]}>
                <View style={styles.pendingIconRow}>
                    <MaterialCommunityIcons name="account-voice" size={20} color="#432818" />
                    <Text style={styles.pendingLabel}>Designing voice</Text>
                </View>
                <Text style={styles.pendingPhase}>
                    {PENDING_PHASES[phaseIndex]}
                    <Text style={styles.pendingDots}>{dots}</Text>
                </Text>
                <View style={styles.pendingSteps}>
                    {PENDING_PHASES.map((_, i) => (
                        <View
                            key={i}
                            style={[styles.pendingStep, i <= phaseIndex && styles.pendingStepActive]}
                        />
                    ))}
                </View>
            </View>
        </Animated.View>
    );
}

export default function VoicePage({ onNavigateTo }) {
    const {
        activeConversation,
        addMessage,
        selectedVoice,
        selectedCreatedVoice,
        addCreatedVoice,
        speak,
        isSpeaking,
        stopSpeaking,
    } = useSessionScope('voice');

    const [inputText, setInputText] = useState('');
    const [processing, setProcessing] = useState(false);
    const [playingId, setPlayingId] = useState(null);
    const [speakingBubbleId, setSpeakingBubbleId] = useState(null);
    const [drawerOpen, setDrawerOpen] = useState(false);
    const [voicePickerOpen, setVoicePickerOpen] = useState(false);
    const scrollRef = useRef(null);
    const soundRef = useRef(null);

    const messages = activeConversation?.messages || [];

    // Clear sample playback on unmount
    useEffect(() => {
        return () => { soundRef.current?.unloadAsync().catch(() => {}); };
    }, []);

    // Stop global speech when switching conversations
    useEffect(() => {
        stopSpeaking();
        setSpeakingBubbleId(null);
    }, [activeConversation?.id, stopSpeaking]);

    // Clear bubble indicator when global speech finishes
    useEffect(() => {
        if (!isSpeaking) setSpeakingBubbleId(null);
    }, [isSpeaking]);

    useEffect(() => {
        if (processing) {
            setTimeout(() => scrollRef.current?.scrollToEnd({ animated: false }), 80);
        }
    }, [processing]);

    const playSample = useCallback(async (id, dataUri) => {
        try {
            if (soundRef.current) {
                await soundRef.current.unloadAsync().catch(() => {});
                soundRef.current = null;
            }
            setPlayingId(id);
            const { sound } = await Audio.Sound.createAsync({ uri: dataUri });
            soundRef.current = sound;

            // didJustFinish is unreliable for data: URIs on Android — fall back to
            // detecting end-of-playback via position/duration so the button always resets.
            const finish = () => {
                setPlayingId((cur) => (cur === id ? null : cur));
                sound.unloadAsync().catch(() => {});
                if (soundRef.current === sound) soundRef.current = null;
            };
            sound.setOnPlaybackStatusUpdate((status) => {
                if (!status.isLoaded) {
                    if (status.error) finish();
                    return;
                }
                const reachedEnd =
                    status.didJustFinish ||
                    (status.durationMillis != null &&
                     !status.isPlaying &&
                     status.positionMillis >= status.durationMillis - 80);
                if (reachedEnd) finish();
            });
            await sound.playAsync();
        } catch (e) {
            console.error('playSample failed', e);
            setPlayingId(null);
        }
    }, []);

    const handleReadAloud = useCallback((id, text) => {
        if (!text || (!selectedVoice && !selectedCreatedVoice)) return;
        setSpeakingBubbleId(id);
        speak(text);
    }, [speak, selectedVoice, selectedCreatedVoice]);

    const handleSend = useCallback(async () => {
        const t = inputText.trim();
        if (!t || processing) return;

        addMessage({ kind: 'user', text: t });
        setInputText('');
        setProcessing(true);
        setTimeout(() => scrollRef.current?.scrollToEnd({ animated: false }), 80);

        const res = await designVoice(t);
        setProcessing(false);

        if (!res.ok) {
            addMessage({ kind: 'error', text: res.message || 'Voice design failed' });
            return;
        }

        const dataUri = `data:${res.data.audio_mime};base64,${res.data.audio_base64}`;
        const voiceMessageId = addMessage({
            kind: 'voice',
            params: res.data.params,
            sampleText: res.data.sample_text,
            dataUri,
        });
        addCreatedVoice({
            display_label: res.data.params.display_label,
            voice_description: res.data.params.voice_description,
            tags: res.data.params.tags,
        });
        setTimeout(() => scrollRef.current?.scrollToEnd({ animated: false }), 80);
        playSample(voiceMessageId, dataUri);
    }, [inputText, processing, playSample, addMessage]);

    return (
        <KeyboardAvoidingView
            style={styles.screen}
            behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
            keyboardVerticalOffset={0}
        >
            <View style={styles.header}>
                <TouchableOpacity
                    style={styles.headerIconBtn}
                    onPress={() => setDrawerOpen(true)}
                    hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
                >
                    <MaterialCommunityIcons name="menu" size={22} color="#2c2c2e" />
                </TouchableOpacity>
                <View style={styles.headerCenter}>
                    <Text style={styles.title} numberOfLines={1}>
                        {activeConversation?.title && activeConversation.title !== 'New conversation'
                            ? activeConversation.title
                            : 'Voice'}
                    </Text>
                    <Text style={styles.subtitle} numberOfLines={1}>
                        {selectedCreatedVoice
                            ? `AI voice: ${selectedCreatedVoice.display_label}`
                            : selectedVoice
                            ? `Read-aloud: ${selectedVoice.name}`
                            : 'Describe a voice — Gemini + ElevenLabs build it'}
                    </Text>
                </View>
                <TouchableOpacity
                    style={styles.headerIconBtn}
                    onPress={() => setVoicePickerOpen(true)}
                    hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
                >
                    <MaterialCommunityIcons name="account-voice" size={20} color="#2c2c2e" />
                </TouchableOpacity>
            </View>

            <ScrollView
                ref={scrollRef}
                style={styles.list}
                contentContainerStyle={styles.listContent}
                showsVerticalScrollIndicator={false}
            >
                {messages.length === 0 && !processing && (
                    <View style={styles.emptyState}>
                        <View style={styles.emptyIconBadge}>
                            <MaterialCommunityIcons name="microphone-outline" size={48} color="#432818" />
                        </View>
                        <Text style={styles.emptyText}>
                            Try: {'"'}a deep mysterious British narrator{'"'}{'\n'}
                            or {'"'}a young Australian woman saying hi{'"'}
                        </Text>
                    </View>
                )}
                {messages.map(msg => {
                    if (msg.kind === 'user') {
                        return (
                            <UserBubble
                                key={msg.id}
                                text={msg.text}
                                onSpeak={(selectedVoice || selectedCreatedVoice) ? () => handleReadAloud(msg.id, msg.text) : undefined}
                                isSpeaking={speakingBubbleId === msg.id && isSpeaking}
                                systemVoiceLabel={selectedCreatedVoice?.display_label ?? selectedVoice?.name}
                            />
                        );
                    }
                    if (msg.kind === 'error') {
                        return (
                            <View key={msg.id} style={[styles.bubbleRow, styles.rowLeft]}>
                                <View style={[styles.bubble, styles.bubbleError]}>
                                    <Text style={styles.errorText}>⚠️ {msg.text}</Text>
                                </View>
                            </View>
                        );
                    }
                    return (
                        <VoiceBubble
                            key={msg.id}
                            message={msg}
                            isPlaying={playingId === msg.id}
                            onPlay={() => playSample(msg.id, msg.dataUri)}
                            onSpeakWithSystem={(selectedVoice || selectedCreatedVoice)
                                ? () => handleReadAloud(msg.id + '-sys', msg.sampleText)
                                : undefined}
                            isSystemSpeaking={speakingBubbleId === msg.id + '-sys' && isSpeaking}
                            systemVoiceLabel={selectedCreatedVoice?.display_label ?? selectedVoice?.name}
                        />
                    );
                })}
                {processing && <PendingBubble />}
            </ScrollView>

            <View style={styles.inputArea}>
                <View style={styles.chatBox}>
                    <TextInput
                        style={styles.textInput}
                        value={inputText}
                        onChangeText={setInputText}
                        placeholder="Describe a voice…"
                        placeholderTextColor="#a09880"
                        returnKeyType="send"
                        onSubmitEditing={handleSend}
                        editable={!processing}
                        multiline={false}
                    />
                    <TouchableOpacity
                        style={[
                            styles.sendBtn,
                            (!inputText.trim() || processing) && styles.sendBtnDisabled,
                        ]}
                        onPress={handleSend}
                        disabled={!inputText.trim() || processing}
                    >
                        {processing
                            ? <ActivityIndicator size="small" color="#FDF0D0" />
                            : <MaterialIcons name="send" size={18} color="#FDF0D0" />}
                    </TouchableOpacity>
                </View>
            </View>

            <View style={styles.navBar}>
                <TouchableOpacity style={styles.navItem} onPress={() => onNavigateTo('translate')}>
                    <Image
                        source={require('../assets/images/signly-logo.png')}
                        style={{ width: 18, height: 18, tintColor: '#817f74' }}
                        resizeMode="contain"
                    />
                    <Text style={styles.navLabelInactive}>Translate</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.navItem} onPress={() => onNavigateTo('animation')}>
                    <MaterialCommunityIcons name="hand-wave" size={18} color="#817f74" />
                    <Text style={styles.navLabelInactive}>Animation</Text>
                </TouchableOpacity>
                <View style={[styles.navItem, styles.navItemActive]}>
                    <MaterialCommunityIcons name="account-voice" size={18} color="#FDF0D0" />
                    <Text style={styles.navLabelActive}>Voice</Text>
                </View>
            </View>

            <HistoryDrawer
                visible={drawerOpen}
                onClose={() => setDrawerOpen(false)}
                onOpenVoicePicker={() => setVoicePickerOpen(true)}
                pageType="voice"
            />
            <VoicePickerModal
                visible={voicePickerOpen}
                onClose={() => setVoicePickerOpen(false)}
            />
        </KeyboardAvoidingView>
    );
}

const styles = StyleSheet.create({
    screen: { flex: 1, backgroundColor: '#F9F6F1' },
    header: {
        width: '100%',
        paddingTop: 60,
        paddingBottom: 8,
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
    headerCenter: { flex: 1, alignItems: 'center' },
    title: { color: '#2c2c2e', fontSize: 22, fontWeight: '700' },
    subtitle: { color: '#a09880', fontSize: 12, marginTop: 2 },

    list: { flex: 1 },
    listContent: {
        flexGrow: 1, justifyContent: 'flex-end',
        paddingHorizontal: 16, paddingTop: 12, paddingBottom: 8, gap: 10,
    },
    emptyState: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 16 },
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
    emptyText: { color: '#a09880', fontSize: 14, textAlign: 'center', lineHeight: 22 },

    bubbleRow: { width: '100%', flexDirection: 'row', alignItems: 'flex-end' },
    rowLeft: { justifyContent: 'flex-start' },
    rowRight: { justifyContent: 'flex-end' },

    bubble: {
        maxWidth: '88%', borderRadius: 18, padding: 14,
        shadowColor: '#000', shadowOpacity: 0.07, shadowRadius: 8, elevation: 3,
    },
    bubbleVoice: {
        backgroundColor: '#ffffff', borderWidth: 1, borderColor: '#432818',
        borderBottomLeftRadius: 4, gap: 10,
    },
    bubbleUser: {
        backgroundColor: '#432818', borderBottomRightRadius: 4,
    },
    bubbleError: {
        backgroundColor: '#fbe8e6', borderWidth: 1, borderColor: '#c0392b',
        borderBottomLeftRadius: 4,
    },
    pendingBubble: { padding: 14, gap: 10, minWidth: 220 },
    pendingIconRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
    pendingLabel: { color: '#432818', fontSize: 13, fontWeight: '700' },
    pendingPhase: { color: '#2c2c2e', fontSize: 14, fontWeight: '500', lineHeight: 20 },
    pendingDots: { color: '#432818', fontWeight: '700' },
    pendingSteps: { flexDirection: 'row', gap: 6, marginTop: 2 },
    pendingStep: { flex: 1, height: 3, borderRadius: 2, backgroundColor: '#e0d8cc' },
    pendingStepActive: { backgroundColor: '#432818' },

    voiceHeader: { flexDirection: 'row', alignItems: 'center', gap: 8 },
    voiceTitle: { color: '#2c2c2e', fontSize: 15, fontWeight: '700', flex: 1 },

    tagsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
    tag: {
        backgroundColor: '#f3ece1', borderRadius: 12,
        paddingHorizontal: 10, paddingVertical: 4,
    },
    tagText: { color: '#6b5a48', fontSize: 11, fontWeight: '600', textTransform: 'capitalize' },

    voiceDescription: { color: '#2c2c2e', fontSize: 13, lineHeight: 19 },
    sampleText: { color: '#6b5a48', fontSize: 12, lineHeight: 18, fontStyle: 'italic' },

    voiceActions: { flexDirection: 'row', alignItems: 'center', gap: 8, flexWrap: 'wrap' },
    playBtn: {
        flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6,
        backgroundColor: '#432818', borderRadius: 18, paddingVertical: 8, paddingHorizontal: 14,
    },
    playBtnText: { color: '#FDF0D0', fontSize: 13, fontWeight: '700' },
    systemPlayBtn: {
        flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6,
        backgroundColor: '#f3ece1', borderRadius: 18, paddingVertical: 8, paddingHorizontal: 12,
        borderWidth: 1, borderColor: '#e0d8cc',
        maxWidth: 180,
    },
    systemPlayBtnText: { color: '#432818', fontSize: 12, fontWeight: '700' },

    userColumn: { alignItems: 'flex-end', maxWidth: '88%', gap: 4 },
    userText: { color: '#FDF0D0', fontSize: 15, lineHeight: 21 },
    userSpeakBtn: {
        flexDirection: 'row', alignItems: 'center', gap: 4,
        backgroundColor: 'rgba(67,40,24,0.08)',
        borderRadius: 12, paddingHorizontal: 10, paddingVertical: 4,
        maxWidth: '100%',
    },
    userSpeakBtnText: { color: '#432818', fontSize: 11, fontWeight: '600' },

    errorText: { color: '#7a1f12', fontSize: 13 },

    inputArea: { paddingHorizontal: 20, paddingBottom: 12 },
    chatBox: {
        height: 52, borderRadius: 26, backgroundColor: '#fff',
        borderWidth: 1, borderColor: '#e0d8cc',
        flexDirection: 'row', alignItems: 'center',
        paddingLeft: 18, paddingRight: 6,
    },
    textInput: { flex: 1, fontSize: 15, color: '#2c2c2e', paddingVertical: 0 },
    sendBtn: {
        width: 40, height: 40, borderRadius: 20,
        backgroundColor: '#432818', justifyContent: 'center', alignItems: 'center',
    },
    sendBtnDisabled: { opacity: 0.4 },

    navBar: {
        width: '94%', marginBottom: 24, alignSelf: 'center',
        backgroundColor: 'rgba(255,255,255,0.55)', borderRadius: 50,
        paddingVertical: 12, paddingHorizontal: 10,
        flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
        shadowColor: '#000', shadowOpacity: 0.08, shadowRadius: 18, elevation: 6,
    },
    navItem: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingVertical: 12 },
    navItemActive: { backgroundColor: 'rgba(100,88,68,0.82)', borderRadius: 20 },
    navLabelInactive: { color: '#817f74', fontSize: 12, fontWeight: '700', marginTop: 6 },
    navLabelActive: { color: '#FDF0D0', fontSize: 12, fontWeight: '700', marginTop: 6 },
});
