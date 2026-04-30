import { CreatedVoice, SystemVoice, useSession } from '@/contexts/SessionContext';
import { MaterialCommunityIcons, MaterialIcons } from '@expo/vector-icons';
import * as Speech from 'expo-speech';
import { useEffect, useMemo, useState } from 'react';
import {
    ActivityIndicator,
    Modal,
    SafeAreaView,
    SectionList,
    StyleSheet,
    Text,
    TouchableOpacity,
    View,
} from 'react-native';

type Props = {
    visible: boolean;
    onClose: () => void;
};

const SAMPLE_TEXT = 'Hello! This is what I sound like.';

function languageLabel(code: string) {
    try {
        const dn = new (Intl as any).DisplayNames(['en'], { type: 'language' });
        return dn.of(code) || code;
    } catch {
        return code;
    }
}

export function VoicePickerModal({ visible, onClose }: Props) {
    const {
        voices,
        voicesLoaded,
        selectedVoiceId,
        setSelectedVoiceId,
        refreshVoices,
        createdVoices,
        selectedCreatedVoice,
        setSelectedCreatedVoice,
    } = useSession();
    const [previewingId, setPreviewingId] = useState<string | null>(null);

    useEffect(() => {
        if (visible && !voicesLoaded) refreshVoices();
    }, [visible, voicesLoaded, refreshVoices]);

    useEffect(() => {
        if (!visible) Speech.stop();
    }, [visible]);

    const sections = useMemo(() => {
        const grouped = new Map<string, SystemVoice[]>();
        for (const v of voices) {
            const key = v.language || 'unknown';
            if (!grouped.has(key)) grouped.set(key, []);
            grouped.get(key)!.push(v);
        }
        return Array.from(grouped.entries())
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([code, data]) => ({
                title: `${languageLabel(code)} (${code})`,
                data: data.sort((a, b) => a.name.localeCompare(b.name)),
            }));
    }, [voices]);

    const previewVoice = (voice: SystemVoice) => {
        Speech.stop();
        setPreviewingId(voice.identifier);
        Speech.speak(SAMPLE_TEXT, {
            voice: voice.identifier,
            language: voice.language,
            onDone: () => setPreviewingId((cur) => (cur === voice.identifier ? null : cur)),
            onStopped: () => setPreviewingId((cur) => (cur === voice.identifier ? null : cur)),
            onError: () => setPreviewingId((cur) => (cur === voice.identifier ? null : cur)),
        });
    };

    return (
        <Modal visible={visible} animationType="slide" onRequestClose={onClose} transparent={false}>
            <SafeAreaView style={styles.screen}>
                <View style={styles.header}>
                    <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
                        <MaterialIcons name="close" size={22} color="#2c2c2e" />
                    </TouchableOpacity>
                    <Text style={styles.title}>Choose voice</Text>
                    <View style={{ width: 40 }} />
                </View>

                {createdVoices.length > 0 && (
                    <View style={styles.myVoicesSection}>
                        <Text style={styles.sectionHeader}>My Voices</Text>
                        {createdVoices.map((cv: CreatedVoice) => {
                            const isSelected = selectedCreatedVoice?.id === cv.id;
                            return (
                                <TouchableOpacity
                                    key={cv.id}
                                    style={[styles.row, isSelected && styles.rowSelected]}
                                    onPress={() => setSelectedCreatedVoice(isSelected ? null : cv)}
                                    activeOpacity={0.7}
                                >
                                    <View style={styles.rowText}>
                                        <Text style={[styles.voiceName, isSelected && styles.voiceNameSelected]}>
                                            {cv.display_label}
                                        </Text>
                                        {cv.tags.length > 0 && (
                                            <Text style={[styles.voiceMeta, isSelected && styles.voiceMetaSelected]}>
                                                {cv.tags.join(' · ')}
                                            </Text>
                                        )}
                                    </View>
                                    <MaterialCommunityIcons
                                        name="account-voice"
                                        size={20}
                                        color={isSelected ? '#FDF0D0' : '#432818'}
                                        style={{ marginLeft: 8 }}
                                    />
                                    {isSelected && (
                                        <MaterialIcons
                                            name="check-circle"
                                            size={20}
                                            color="#FDF0D0"
                                            style={{ marginLeft: 6 }}
                                        />
                                    )}
                                </TouchableOpacity>
                            );
                        })}
                    </View>
                )}

                {!voicesLoaded ? (
                    <View style={styles.loading}>
                        <ActivityIndicator size="large" color="#432818" />
                        <Text style={styles.loadingText}>Loading voices…</Text>
                    </View>
                ) : voices.length === 0 ? (
                    <View style={styles.loading}>
                        <Text style={styles.loadingText}>
                            No voices available on this device.
                        </Text>
                    </View>
                ) : (
                    <SectionList
                        sections={sections}
                        keyExtractor={(v) => v.identifier}
                        contentContainerStyle={styles.listContent}
                        stickySectionHeadersEnabled={false}
                        renderSectionHeader={({ section }) => (
                            <Text style={styles.sectionHeader}>{section.title}</Text>
                        )}
                        renderItem={({ item }) => {
                            const isSelected = item.identifier === selectedVoiceId;
                            const isPreviewing = item.identifier === previewingId;
                            return (
                                <TouchableOpacity
                                    style={[styles.row, isSelected && styles.rowSelected]}
                                    onPress={() => { setSelectedVoiceId(item.identifier); setSelectedCreatedVoice(null); }}
                                    activeOpacity={0.7}
                                >
                                    <View style={styles.rowText}>
                                        <Text
                                            style={[styles.voiceName, isSelected && styles.voiceNameSelected]}
                                        >
                                            {item.name}
                                        </Text>
                                        <Text
                                            style={[styles.voiceMeta, isSelected && styles.voiceMetaSelected]}
                                        >
                                            {item.quality || 'Default'}
                                        </Text>
                                    </View>
                                    <TouchableOpacity
                                        style={styles.previewBtn}
                                        onPress={() => previewVoice(item)}
                                        hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
                                    >
                                        {isPreviewing ? (
                                            <ActivityIndicator size="small" color="#432818" />
                                        ) : (
                                            <MaterialCommunityIcons
                                                name="play-circle"
                                                size={26}
                                                color={isSelected ? '#FDF0D0' : '#432818'}
                                            />
                                        )}
                                    </TouchableOpacity>
                                    {isSelected && (
                                        <MaterialIcons
                                            name="check-circle"
                                            size={20}
                                            color="#FDF0D0"
                                            style={{ marginLeft: 8 }}
                                        />
                                    )}
                                </TouchableOpacity>
                            );
                        }}
                    />
                )}
            </SafeAreaView>
        </Modal>
    );
}

const styles = StyleSheet.create({
    screen: { flex: 1, backgroundColor: '#F9F6F1' },
    header: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingHorizontal: 12,
        paddingTop: 12,
        paddingBottom: 12,
        borderBottomWidth: 1,
        borderBottomColor: '#e8e1d3',
    },
    closeBtn: {
        width: 40,
        height: 40,
        borderRadius: 20,
        justifyContent: 'center',
        alignItems: 'center',
    },
    title: { fontSize: 17, fontWeight: '700', color: '#2c2c2e' },

    loading: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 10 },
    loadingText: { color: '#6b5a48', fontSize: 14 },

    myVoicesSection: { paddingHorizontal: 12, paddingTop: 8, paddingBottom: 4 },
    listContent: { paddingHorizontal: 12, paddingBottom: 24 },
    sectionHeader: {
        fontSize: 12,
        fontWeight: '700',
        color: '#6b5a48',
        textTransform: 'uppercase',
        letterSpacing: 0.5,
        marginTop: 16,
        marginBottom: 6,
        paddingHorizontal: 4,
    },
    row: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#fff',
        borderWidth: 1,
        borderColor: '#e0d8cc',
        borderRadius: 14,
        paddingHorizontal: 14,
        paddingVertical: 10,
        marginBottom: 6,
    },
    rowSelected: {
        backgroundColor: '#432818',
        borderColor: '#432818',
    },
    rowText: { flex: 1 },
    voiceName: { color: '#2c2c2e', fontSize: 15, fontWeight: '600' },
    voiceNameSelected: { color: '#FDF0D0' },
    voiceMeta: { color: '#a09880', fontSize: 11, marginTop: 2 },
    voiceMetaSelected: { color: 'rgba(253,240,208,0.7)' },
    previewBtn: {
        width: 36, height: 36, justifyContent: 'center', alignItems: 'center',
    },
});
