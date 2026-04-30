import { Audio } from 'expo-av';
import * as Speech from 'expo-speech';
import {
    createContext,
    ReactNode,
    useCallback,
    useContext,
    useEffect,
    useMemo,
    useRef,
    useState,
} from 'react';
import { speakWithDesignedVoice } from '@/lib/api';

// In-memory only — wiped on every full app reload. That's intentional:
// no auth, no AsyncStorage, every cold start gives a clean demo.

export type PageType = 'translate' | 'voice' | 'animation';

export type SystemVoice = {
    identifier: string;
    name: string;
    language: string;
    quality?: string;
};

export type CreatedVoice = {
    id: string;
    display_label: string;
    voice_description: string;
    tags: string[];
};

// Each page stores messages with its own shape; we keep the type loose.
export type ConversationMessage = {
    id: string;
    [key: string]: any;
};

export type Conversation = {
    id: string;
    pageType: PageType;
    title: string;
    createdAt: number;
    messages: ConversationMessage[];
    sessionId?: string; // optional backend session id (TranslatePage uses this)
};

type SessionContextValue = {
    conversations: Conversation[];
    activeIdByPage: Record<PageType, string | null>;
    selectedVoiceId: string | null;
    selectedVoice: SystemVoice | null;
    voices: SystemVoice[];
    voicesLoaded: boolean;
    createdVoices: CreatedVoice[];
    selectedCreatedVoice: CreatedVoice | null;

    newConversation: (pageType: PageType, opts?: { sessionId?: string }) => string;
    selectConversation: (id: string) => void;
    addMessage: (
        pageType: PageType,
        msg: Omit<ConversationMessage, 'id'>,
    ) => string;
    updateConversation: (
        id: string,
        patch: Partial<Pick<Conversation, 'title' | 'sessionId'>>,
    ) => void;
    setSelectedVoiceId: (id: string | null) => void;
    refreshVoices: () => Promise<void>;
    addCreatedVoice: (voice: Omit<CreatedVoice, 'id'>) => string;
    setSelectedCreatedVoice: (voice: CreatedVoice | null) => void;
    isSpeaking: boolean;
    speak: (text: string) => Promise<void>;
    stopSpeaking: () => Promise<void>;
};

const SessionContext = createContext<SessionContextValue | null>(null);

const newId = (prefix: string) =>
    `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;

function deriveTitle(pageType: PageType, messages: ConversationMessage[]): string {
    if (pageType === 'voice') {
        const firstUser = messages.find((m) => m.kind === 'user');
        if (firstUser?.text) {
            const t = firstUser.text.trim();
            return t.length > 40 ? t.slice(0, 40) + '…' : t;
        }
    } else if (pageType === 'translate') {
        // Prefer the first speech transcript; fall back to first sign english.
        const firstSpeech = messages.find((m) => m.type === 'speech_to_text' && m.transcript);
        if (firstSpeech?.transcript) {
            const t = firstSpeech.transcript.trim();
            return t.length > 40 ? t.slice(0, 40) + '…' : t;
        }
        const firstSign = messages.find((m) => m.type === 'sign_to_text');
        if (firstSign?.english) {
            const t = firstSign.english.trim();
            return t.length > 40 ? t.slice(0, 40) + '…' : t;
        }
    } else if (pageType === 'animation') {
        const firstPrompt = messages.find((m) => m.kind === 'animation' && m.text);
        if (firstPrompt?.text) {
            const t = firstPrompt.text.trim();
            return t.length > 40 ? t.slice(0, 40) + '…' : t;
        }
    }
    return 'New conversation';
}

export function SessionProvider({ children }: { children: ReactNode }) {
    const [conversations, setConversations] = useState<Conversation[]>([]);
    const [activeIdByPage, setActiveIdByPage] = useState<Record<PageType, string | null>>({
        translate: null,
        voice: null,
        animation: null,
    });
    const [selectedVoiceId, setSelectedVoiceIdState] = useState<string | null>(null);
    const [voices, setVoices] = useState<SystemVoice[]>([]);
    const [voicesLoaded, setVoicesLoaded] = useState(false);
    const [createdVoices, setCreatedVoices] = useState<CreatedVoice[]>([]);
    const [selectedCreatedVoice, setSelectedCreatedVoiceState] = useState<CreatedVoice | null>(null);
    const [isSpeaking, setIsSpeaking] = useState(false);
    const speechSoundRef = useRef<Audio.Sound | null>(null);
    // Stable refs so speak() always reads the latest voice without recreating
    const createdVoiceRef = useRef<CreatedVoice | null>(null);
    const systemVoiceRef = useRef<SystemVoice | null>(null);

    // Mirror activeIdByPage in a ref so addMessage can read the latest
    // value synchronously. Two addMessage calls back-to-back must agree on
    // the same conversation id even before React flushes the auto-create.
    const activeIdRef = useRef(activeIdByPage);
    useEffect(() => { activeIdRef.current = activeIdByPage; }, [activeIdByPage]);

    const refreshVoices = useCallback(async () => {
        try {
            const list = await Speech.getAvailableVoicesAsync();
            const mapped: SystemVoice[] = (list || []).map((v: any) => ({
                identifier: v.identifier,
                name: v.name || v.identifier,
                language: v.language || 'unknown',
                quality: v.quality,
            }));
            setVoices(mapped);
            setVoicesLoaded(true);
            setSelectedVoiceIdState((cur) => {
                if (cur && mapped.some((v) => v.identifier === cur)) return cur;
                const en = mapped.filter((v) => v.language?.startsWith('en'));
                const enhanced = en.find((v) => v.quality === 'Enhanced');
                return enhanced?.identifier || en[0]?.identifier || mapped[0]?.identifier || null;
            });
        } catch (e) {
            console.error('refreshVoices failed', e);
            setVoicesLoaded(true);
        }
    }, []);

    useEffect(() => { refreshVoices(); }, [refreshVoices]);

    const newConversation = useCallback<SessionContextValue['newConversation']>(
        (pageType, opts) => {
            const id = newId('c');
            const convo: Conversation = {
                id,
                pageType,
                title: 'New conversation',
                createdAt: Date.now(),
                messages: [],
                sessionId: opts?.sessionId,
            };
            setConversations((prev) => [convo, ...prev]);
            activeIdRef.current = { ...activeIdRef.current, [pageType]: id };
            setActiveIdByPage((prev) => ({ ...prev, [pageType]: id }));
            return id;
        },
        [],
    );

    const selectConversation = useCallback((id: string) => {
        // Find the conversation to know its pageType.
        setConversations((prev) => {
            const found = prev.find((c) => c.id === id);
            if (found) {
                activeIdRef.current = { ...activeIdRef.current, [found.pageType]: id };
                setActiveIdByPage((cur) => ({ ...cur, [found.pageType]: id }));
            }
            return prev;
        });
    }, []);

    const addMessage = useCallback<SessionContextValue['addMessage']>((pageType, msg) => {
        const messageId = newId('m');
        const fullMsg: ConversationMessage = { ...msg, id: messageId };

        let targetId = activeIdRef.current[pageType];
        let createdConvo: Conversation | null = null;
        if (!targetId) {
            targetId = newId('c');
            createdConvo = {
                id: targetId,
                pageType,
                title: 'New conversation',
                createdAt: Date.now(),
                messages: [],
            };
            activeIdRef.current = { ...activeIdRef.current, [pageType]: targetId };
            setActiveIdByPage((prev) => ({ ...prev, [pageType]: targetId! }));
        }

        setConversations((prev) => {
            const convos = createdConvo && !prev.some((c) => c.id === createdConvo!.id)
                ? [createdConvo, ...prev]
                : prev;
            return convos.map((c) => {
                if (c.id !== targetId) return c;
                const nextMessages = [...c.messages, fullMsg];
                return {
                    ...c,
                    messages: nextMessages,
                    title: c.title === 'New conversation'
                        ? deriveTitle(c.pageType, nextMessages)
                        : c.title,
                };
            });
        });

        return messageId;
    }, []);

    const updateConversation = useCallback<SessionContextValue['updateConversation']>(
        (id, patch) => {
            setConversations((prev) =>
                prev.map((c) => (c.id === id ? { ...c, ...patch } : c)),
            );
        },
        [],
    );

    const setSelectedVoiceId = useCallback((id: string | null) => {
        setSelectedVoiceIdState(id);
        setSelectedCreatedVoiceState(null);
    }, []);

    const addCreatedVoice = useCallback((voice: Omit<CreatedVoice, 'id'>): string => {
        const id = newId('cv');
        setCreatedVoices((prev) => [{ ...voice, id }, ...prev]);
        return id;
    }, []);

    const setSelectedCreatedVoice = useCallback((voice: CreatedVoice | null) => {
        setSelectedCreatedVoiceState(voice);
    }, []);

    // Keep stable refs in sync so speak() never needs to be recreated
    useEffect(() => { createdVoiceRef.current = selectedCreatedVoice; }, [selectedCreatedVoice]);
    useEffect(() => { systemVoiceRef.current = selectedVoice; }, [selectedVoice]);

    const stopSpeaking = useCallback(async () => {
        Speech.stop();
        if (speechSoundRef.current) {
            await speechSoundRef.current.unloadAsync().catch(() => {});
            speechSoundRef.current = null;
        }
        setIsSpeaking(false);
    }, []);

    const speak = useCallback(async (text: string): Promise<void> => {
        if (!text.trim()) return;
        await stopSpeaking();

        const createdVoice = createdVoiceRef.current;
        const systemVoice = systemVoiceRef.current;
        setIsSpeaking(true);

        if (createdVoice) {
            try {
                const res = await speakWithDesignedVoice(createdVoice.voice_description, text);
                if (!res.ok) { setIsSpeaking(false); return; }
                const dataUri = `data:${res.data.audio_mime};base64,${res.data.audio_base64}`;
                const { sound } = await Audio.Sound.createAsync({ uri: dataUri });
                speechSoundRef.current = sound;
                await new Promise<void>((resolve) => {
                    const finish = () => {
                        setIsSpeaking(false);
                        sound.unloadAsync().catch(() => {});
                        if (speechSoundRef.current === sound) speechSoundRef.current = null;
                        resolve();
                    };
                    sound.setOnPlaybackStatusUpdate((status) => {
                        if (!status.isLoaded) { if (status.error) finish(); return; }
                        const done =
                            status.didJustFinish ||
                            (status.durationMillis != null &&
                             !status.isPlaying &&
                             status.positionMillis >= status.durationMillis - 80);
                        if (done) finish();
                    });
                    sound.playAsync();
                });
            } catch {
                setIsSpeaking(false);
            }
            return;
        }

        await new Promise<void>((resolve) => {
            const done = () => { setIsSpeaking(false); resolve(); };
            Speech.speak(text, {
                ...(systemVoice
                    ? { voice: systemVoice.identifier, language: systemVoice.language }
                    : {}),
                onDone: done,
                onStopped: done,
                onError: done,
            });
        });
    }, [stopSpeaking]);

    const selectedVoice = useMemo(
        () => voices.find((v) => v.identifier === selectedVoiceId) || null,
        [voices, selectedVoiceId],
    );

    const value = useMemo<SessionContextValue>(
        () => ({
            conversations,
            activeIdByPage,
            selectedVoiceId,
            selectedVoice,
            voices,
            voicesLoaded,
            createdVoices,
            selectedCreatedVoice,
            newConversation,
            selectConversation,
            addMessage,
            updateConversation,
            setSelectedVoiceId,
            refreshVoices,
            addCreatedVoice,
            setSelectedCreatedVoice,
            isSpeaking,
            speak,
            stopSpeaking,
        }),
        [
            conversations, activeIdByPage,
            selectedVoiceId, selectedVoice, voices, voicesLoaded,
            createdVoices, selectedCreatedVoice,
            newConversation, selectConversation, addMessage, updateConversation,
            setSelectedVoiceId, refreshVoices, addCreatedVoice, setSelectedCreatedVoice,
            isSpeaking, speak, stopSpeaking,
        ],
    );

    return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
    const ctx = useContext(SessionContext);
    if (!ctx) throw new Error('useSession must be used inside <SessionProvider>');
    return ctx;
}

// Page-scoped helper: filters conversations to the given pageType and
// pre-binds addMessage/newConversation so callers don't have to pass it.
export function useSessionScope(pageType: PageType) {
    const ctx = useSession();
    const conversations = useMemo(
        () => ctx.conversations.filter((c) => c.pageType === pageType),
        [ctx.conversations, pageType],
    );
    const activeConversationId = ctx.activeIdByPage[pageType];
    const activeConversation = useMemo(
        () => conversations.find((c) => c.id === activeConversationId) || null,
        [conversations, activeConversationId],
    );

    const addMessage = useCallback(
        (msg: Omit<ConversationMessage, 'id'>) => ctx.addMessage(pageType, msg),
        [ctx, pageType],
    );
    const newConversation = useCallback(
        (opts?: { sessionId?: string }) => ctx.newConversation(pageType, opts),
        [ctx, pageType],
    );

    return {
        conversations,
        activeConversationId,
        activeConversation,
        addMessage,
        newConversation,
        selectConversation: ctx.selectConversation,
        updateConversation: ctx.updateConversation,

        // Voice picker concerns are global, exposed here for convenience.
        selectedVoice: ctx.selectedVoice,
        selectedVoiceId: ctx.selectedVoiceId,
        createdVoices: ctx.createdVoices,
        selectedCreatedVoice: ctx.selectedCreatedVoice,
        addCreatedVoice: ctx.addCreatedVoice,
        setSelectedCreatedVoice: ctx.setSelectedCreatedVoice,
        isSpeaking: ctx.isSpeaking,
        speak: ctx.speak,
        stopSpeaking: ctx.stopSpeaking,
    };
}
