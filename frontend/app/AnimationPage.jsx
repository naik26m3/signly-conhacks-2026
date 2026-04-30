import { useSpeechUpload } from '@/hooks/use-speech-upload';
import { MaterialCommunityIcons, MaterialIcons } from '@expo/vector-icons';
import { useCallback, useMemo, useRef, useState } from 'react';
import {
    ActivityIndicator,
    StyleSheet,
    Text,
    TextInput,
    TouchableOpacity,
    View,
} from 'react-native';
import { WebView } from 'react-native-webview';

const SIGN_MT_BASE = 'https://sign.mt/';

function buildSignMtUrl(text) {
    const params = new URLSearchParams({
        spl: 'en',
        sil: 'ase',
        text: text || '',
    });
    return `${SIGN_MT_BASE}?${params.toString()}`;
}

export default function AnimationPage({ onNavigateTo }) {
    const [inputText, setInputText] = useState('');
    const [submittedText, setSubmittedText] = useState('');
    const [webviewLoading, setWebviewLoading] = useState(false);
    const webviewRef = useRef(null);

    const { isRecording, isProcessing: processingMic, start: startMic, stop: stopMic } = useSpeechUpload();

    const url = useMemo(() => buildSignMtUrl(submittedText), [submittedText]);

    const handleSend = useCallback(() => {
        const t = inputText.trim();
        if (!t) return;
        setSubmittedText(t);
    }, [inputText]);

    const handleMicPress = useCallback(async () => {
        if (isRecording) {
            const result = await stopMic();
            if (result?.transcript) {
                setInputText(result.transcript);
                setSubmittedText(result.transcript);
            }
        } else {
            await startMic();
        }
    }, [isRecording, startMic, stopMic]);

    const hasContent = !!submittedText;

    return (
        <View style={styles.screen}>
            <View style={styles.header}>
                <Text style={styles.title}>Animation</Text>
                <Text style={styles.subtitle}>Powered by sign.mt</Text>
            </View>

            {/* WebView area */}
            <View style={styles.webviewWrap}>
                {!hasContent ? (
                    <View style={styles.emptyState}>
                        <Text style={styles.emptyEmoji}>🤟</Text>
                        <Text style={styles.emptyText}>Type or speak to see{'\n'}the ASL avatar sign it</Text>
                    </View>
                ) : (
                    <>
                        <WebView
                            ref={webviewRef}
                            source={{ uri: url }}
                            style={styles.webview}
                            javaScriptEnabled
                            domStorageEnabled
                            mediaPlaybackRequiresUserAction={false}
                            allowsInlineMediaPlayback
                            onLoadStart={() => setWebviewLoading(true)}
                            onLoadEnd={() => setWebviewLoading(false)}
                            startInLoadingState
                            renderLoading={() => (
                                <View style={styles.webviewLoader}>
                                    <ActivityIndicator size="large" color="#432818" />
                                </View>
                            )}
                        />
                        {webviewLoading && (
                            <View style={styles.webviewLoaderOverlay} pointerEvents="none">
                                <ActivityIndicator size="small" color="#432818" />
                            </View>
                        )}
                    </>
                )}
            </View>

            {/* Input area */}
            <View style={styles.inputArea}>
                <View style={styles.inputRow}>
                    <TextInput
                        style={styles.textInput}
                        value={inputText}
                        onChangeText={setInputText}
                        placeholder="Type something to sign…"
                        placeholderTextColor="#a09880"
                        returnKeyType="send"
                        onSubmitEditing={handleSend}
                        editable={!processingMic}
                    />
                    <TouchableOpacity
                        style={[styles.sendBtn, !inputText.trim() && styles.sendBtnDisabled]}
                        onPress={handleSend}
                        disabled={!inputText.trim()}
                    >
                        <MaterialIcons name="send" size={20} color="#FDF0D0" />
                    </TouchableOpacity>
                </View>

                <TouchableOpacity
                    style={[
                        styles.fabMic,
                        isRecording && styles.fabMicRecording,
                        processingMic && styles.fabDisabled,
                    ]}
                    onPress={handleMicPress}
                >
                    {processingMic
                        ? <ActivityIndicator size="small" color="#fff" />
                        : <MaterialCommunityIcons
                            name={isRecording ? 'stop' : 'microphone'}
                            size={24}
                            color="#ffffff"
                          />
                    }
                </TouchableOpacity>
            </View>

            {/* Nav bar */}
            <View style={styles.navBar}>
                <TouchableOpacity style={styles.navItem} onPress={() => onNavigateTo('translate')}>
                    <MaterialIcons name="translate" size={18} color="#817f74" />
                    <Text style={styles.navLabelInactive}>Translate</Text>
                </TouchableOpacity>
                <View style={[styles.navItem, styles.navItemActive]}>
                    <MaterialCommunityIcons name="hand-wave" size={18} color="#FDF0D0" />
                    <Text style={styles.navLabelActive}>Animation</Text>
                </View>
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    screen: {
        flex: 1,
        backgroundColor: '#F9F6F1',
    },
    header: {
        width: '100%',
        paddingTop: 60,
        paddingBottom: 8,
        alignItems: 'center',
    },
    title: {
        color: '#2c2c2e',
        fontSize: 22,
        fontWeight: '700',
    },
    subtitle: {
        color: '#a09880',
        fontSize: 12,
        marginTop: 2,
    },

    // ── webview ──
    webviewWrap: {
        flex: 1,
        marginHorizontal: 16,
        marginVertical: 12,
        borderRadius: 20,
        overflow: 'hidden',
        backgroundColor: '#fff',
        borderWidth: 1,
        borderColor: '#e0d8cc',
        shadowColor: '#000',
        shadowOpacity: 0.08,
        shadowRadius: 12,
        elevation: 4,
    },
    webview: {
        flex: 1,
        backgroundColor: '#fff',
    },
    webviewLoader: {
        ...StyleSheet.absoluteFillObject,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: '#fff',
    },
    webviewLoaderOverlay: {
        position: 'absolute',
        top: 12,
        right: 12,
    },
    emptyState: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
        gap: 12,
    },
    emptyEmoji: {
        fontSize: 64,
    },
    emptyText: {
        color: '#a09880',
        fontSize: 15,
        textAlign: 'center',
        lineHeight: 24,
    },

    // ── input ──
    inputArea: {
        paddingHorizontal: 20,
        paddingBottom: 12,
        gap: 12,
        alignItems: 'center',
    },
    inputRow: {
        width: '100%',
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
    },
    textInput: {
        flex: 1,
        height: 48,
        borderRadius: 24,
        paddingHorizontal: 18,
        backgroundColor: '#fff',
        borderWidth: 1,
        borderColor: '#e0d8cc',
        fontSize: 15,
        color: '#2c2c2e',
    },
    sendBtn: {
        width: 48,
        height: 48,
        borderRadius: 24,
        backgroundColor: '#432818',
        justifyContent: 'center',
        alignItems: 'center',
    },
    sendBtnDisabled: {
        opacity: 0.4,
    },
    fabMic: {
        width: 60,
        height: 60,
        borderRadius: 30,
        backgroundColor: '#3d2c22',
        justifyContent: 'center',
        alignItems: 'center',
        shadowColor: '#b47e5f',
        shadowOpacity: 0.8,
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
