import { PageType, useSessionScope } from '@/contexts/SessionContext';
import { MaterialCommunityIcons, MaterialIcons } from '@expo/vector-icons';
import { useEffect, useRef } from 'react';
import {
    Animated,
    Easing,
    Modal,
    Pressable,
    ScrollView,
    StyleSheet,
    Text,
    TouchableOpacity,
    View,
} from 'react-native';

type Props = {
    visible: boolean;
    onClose: () => void;
    onOpenVoicePicker: () => void;
    pageType: PageType;
    onSelectConversation?: (id: string) => void;
    onNewConversation?: () => void;
};

const DRAWER_WIDTH = 300;

function relativeTime(ts: number) {
    const diff = Date.now() - ts;
    const m = Math.floor(diff / 60000);
    if (m < 1) return 'just now';
    if (m < 60) return `${m}m ago`;
    const h = Math.floor(m / 60);
    if (h < 24) return `${h}h ago`;
    return new Date(ts).toLocaleDateString();
}

export function HistoryDrawer({
    visible,
    onClose,
    onOpenVoicePicker,
    pageType,
    onSelectConversation,
    onNewConversation,
}: Props) {
    const {
        conversations,
        activeConversationId,
        selectConversation,
        newConversation,
        selectedVoice,
    } = useSessionScope(pageType);

    const slide = useRef(new Animated.Value(-DRAWER_WIDTH)).current;
    const fade = useRef(new Animated.Value(0)).current;

    useEffect(() => {
        Animated.parallel([
            Animated.timing(slide, {
                toValue: visible ? 0 : -DRAWER_WIDTH,
                duration: 240,
                easing: Easing.out(Easing.cubic),
                useNativeDriver: true,
            }),
            Animated.timing(fade, {
                toValue: visible ? 1 : 0,
                duration: 200,
                useNativeDriver: true,
            }),
        ]).start();
    }, [visible, slide, fade]);

    const handleSelect = (id: string) => {
        if (onSelectConversation) {
            onSelectConversation(id);
        } else {
            selectConversation(id);
        }
        onClose();
    };

    const handleNew = () => {
        if (onNewConversation) {
            onNewConversation();
        } else {
            newConversation();
        }
        onClose();
    };

    return (
        <Modal visible={visible} transparent animationType="none" onRequestClose={onClose}>
            <View style={styles.root}>
                <Animated.View style={[styles.scrim, { opacity: fade }]}>
                    <Pressable style={StyleSheet.absoluteFill} onPress={onClose} />
                </Animated.View>

                <Animated.View
                    style={[
                        styles.drawer,
                        { transform: [{ translateX: slide }] },
                    ]}
                >
                    <View style={styles.header}>
                        <Text style={styles.headerTitle}>History</Text>
                        <TouchableOpacity onPress={handleNew} style={styles.newBtn}>
                            <MaterialIcons name="add" size={18} color="#FDF0D0" />
                            <Text style={styles.newBtnText}>New</Text>
                        </TouchableOpacity>
                    </View>

                    <ScrollView style={styles.list} contentContainerStyle={styles.listContent}>
                        {conversations.length === 0 && (
                            <Text style={styles.empty}>
                                No conversations yet.{'\n'}Start one to see it here.
                            </Text>
                        )}
                        {conversations.map((c) => {
                            const isActive = c.id === activeConversationId;
                            return (
                                <TouchableOpacity
                                    key={c.id}
                                    onPress={() => handleSelect(c.id)}
                                    style={[styles.item, isActive && styles.itemActive]}
                                    activeOpacity={0.7}
                                >
                                    <MaterialCommunityIcons
                                        name="chat-outline"
                                        size={16}
                                        color={isActive ? '#FDF0D0' : '#6b5a48'}
                                    />
                                    <View style={styles.itemTextWrap}>
                                        <Text
                                            style={[styles.itemTitle, isActive && styles.itemTitleActive]}
                                            numberOfLines={1}
                                        >
                                            {c.title}
                                        </Text>
                                        <Text
                                            style={[styles.itemMeta, isActive && styles.itemMetaActive]}
                                        >
                                            {c.messages.length} msg · {relativeTime(c.createdAt)}
                                        </Text>
                                    </View>
                                </TouchableOpacity>
                            );
                        })}
                    </ScrollView>

                    <View style={styles.footer}>
                        <TouchableOpacity
                            style={styles.voiceRow}
                            onPress={() => {
                                onClose();
                                // small delay so the drawer slide-out doesn't fight the modal-open
                                setTimeout(onOpenVoicePicker, 220);
                            }}
                            activeOpacity={0.7}
                        >
                            <MaterialCommunityIcons name="account-voice" size={18} color="#432818" />
                            <View style={styles.voiceTextWrap}>
                                <Text style={styles.voiceLabel}>Read-aloud voice</Text>
                                <Text style={styles.voiceValue} numberOfLines={1}>
                                    {selectedVoice
                                        ? `${selectedVoice.name} · ${selectedVoice.language}`
                                        : 'None selected'}
                                </Text>
                            </View>
                            <MaterialIcons name="chevron-right" size={20} color="#817f74" />
                        </TouchableOpacity>
                    </View>
                </Animated.View>
            </View>
        </Modal>
    );
}

const styles = StyleSheet.create({
    root: { flex: 1, flexDirection: 'row' },
    scrim: {
        ...StyleSheet.absoluteFillObject,
        backgroundColor: 'rgba(0,0,0,0.45)',
    },
    drawer: {
        width: DRAWER_WIDTH,
        height: '100%',
        backgroundColor: '#F9F6F1',
        borderRightWidth: 1,
        borderRightColor: '#e0d8cc',
        paddingTop: 60,
        flexDirection: 'column',
    },
    header: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingHorizontal: 16,
        paddingBottom: 12,
        borderBottomWidth: 1,
        borderBottomColor: '#e8e1d3',
    },
    headerTitle: { fontSize: 18, fontWeight: '700', color: '#2c2c2e' },
    newBtn: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
        backgroundColor: '#432818',
        paddingHorizontal: 10,
        paddingVertical: 6,
        borderRadius: 14,
    },
    newBtnText: { color: '#FDF0D0', fontSize: 12, fontWeight: '700' },

    list: { flex: 1 },
    listContent: { paddingVertical: 8 },
    empty: {
        color: '#a09880',
        fontSize: 13,
        textAlign: 'center',
        marginTop: 40,
        lineHeight: 20,
    },
    item: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 10,
        paddingVertical: 10,
        paddingHorizontal: 16,
    },
    itemActive: { backgroundColor: '#432818' },
    itemTextWrap: { flex: 1 },
    itemTitle: { color: '#2c2c2e', fontSize: 14, fontWeight: '600' },
    itemTitleActive: { color: '#FDF0D0' },
    itemMeta: { color: '#a09880', fontSize: 11, marginTop: 2 },
    itemMetaActive: { color: 'rgba(253,240,208,0.7)' },

    footer: {
        borderTopWidth: 1,
        borderTopColor: '#e8e1d3',
        padding: 12,
    },
    voiceRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 10,
        backgroundColor: '#fff',
        borderWidth: 1,
        borderColor: '#e0d8cc',
        borderRadius: 14,
        paddingHorizontal: 12,
        paddingVertical: 10,
    },
    voiceTextWrap: { flex: 1 },
    voiceLabel: { color: '#6b5a48', fontSize: 11, fontWeight: '600' },
    voiceValue: { color: '#2c2c2e', fontSize: 13, fontWeight: '600', marginTop: 2 },
});
