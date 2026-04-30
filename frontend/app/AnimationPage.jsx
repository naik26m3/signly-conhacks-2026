// Credit to https://sign.mt/

import { HistoryDrawer } from '@/components/history-drawer';
import { VoicePickerModal } from '@/components/voice-picker-modal';
import { useSessionScope } from '@/contexts/SessionContext';
import { MaterialCommunityIcons, MaterialIcons } from '@expo/vector-icons';
import * as Speech from 'expo-speech';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
    ActivityIndicator,
    Image,
    Keyboard,
    KeyboardAvoidingView,
    Platform,
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

// Strip sign.mt's own UI chrome (language picker, input bar, mic, download/share FABs)
// so only the avatar viewer is visible. Our native input + mic drive everything via the URL.
const HIDE_CHROME_JS = `
(function () {
  var css = [
    /* language picker / top bar */
    'app-language-selectors',
    'app-spoken-to-signed',
    'app-signed-to-spoken',
    'mat-toolbar',
    'header',
    /* input area at the bottom */
    'app-input-mode',
    'app-desktop-input',
    'app-mobile-input',
    'app-spoken-language-input',
    'app-text-input',
    'app-mic-input',
    'app-spoken-language-mic-input',
    /* output FABs (download, share, orientation) */
    'app-video-controls',
    'app-pose-viewer-controls',
    'app-download-button',
    'app-share-button',
    'button[mat-fab]',
    'button[mat-mini-fab]',
    /* generic fallbacks */
    '.mat-mdc-fab',
    '.mat-mdc-mini-fab',
    '.language-selectors',
    '.input-mode',
    '.controls'
  ].join(',') + ' { display: none !important; visibility: hidden !important; }';

  var fillCss =
    'app-translate, app-translate-desktop, app-translate-mobile,' +
    'app-signed-language-output, app-pose-viewer, app-video {' +
    '  width: 100% !important; height: 100% !important;' +
    '  max-width: none !important; max-height: none !important;' +
    '}' +
    'html, body { background: #F9F6F1 !important; margin: 0 !important; padding: 0 !important; overflow: hidden !important; }';

  function apply() {
    var style = document.getElementById('signly-hide-chrome');
    if (!style) {
      style = document.createElement('style');
      style.id = 'signly-hide-chrome';
      style.textContent = css + fillCss;
      (document.head || document.documentElement).appendChild(style);
    }
  }

  apply();
  // Angular hydrates after first paint — keep re-applying as the DOM changes.
  new MutationObserver(apply).observe(document.documentElement, { childList: true, subtree: true });
  true;
})();
`;

export default function AnimationPage({ onNavigateTo }) {
    const {
        activeConversation,
        addMessage,
        newConversation,
        selectConversation,
        selectedVoice,
    } = useSessionScope('animation');

    const [inputText, setInputText] = useState('');
    const [submittedText, setSubmittedText] = useState('');
    const [webviewLoading, setWebviewLoading] = useState(false);
    const [drawerOpen, setDrawerOpen] = useState(false);
    const [voicePickerOpen, setVoicePickerOpen] = useState(false);
    const webviewRef = useRef(null);

    const url = useMemo(() => buildSignMtUrl(submittedText), [submittedText]);
    const title = activeConversation?.title && activeConversation.title !== 'New conversation'
        ? activeConversation.title
        : 'Animation';
    const latestConversationText = useMemo(() => {
        const animationMessages = activeConversation?.messages
            ?.filter((m) => m.kind === 'animation' && m.text) || [];
        return animationMessages[animationMessages.length - 1]?.text || '';
    }, [activeConversation?.messages]);

    useEffect(() => {
        setSubmittedText(latestConversationText);
        setInputText(latestConversationText);
        Speech.stop();
    }, [activeConversation?.id, latestConversationText]);

    const handleSend = useCallback(() => {
        const t = inputText.trim();
        if (!t) return;
        addMessage({ kind: 'animation', text: t });
        setSubmittedText(t);
        Keyboard.dismiss();
    }, [inputText, addMessage]);

    const handleNewConversation = useCallback(() => {
        newConversation();
        setInputText('');
        setSubmittedText('');
        Speech.stop();
    }, [newConversation]);

    const handleSelectConversation = useCallback((id) => {
        selectConversation(id);
        Speech.stop();
    }, [selectConversation]);

    const hasContent = !!submittedText;

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
                    <Text style={styles.title} numberOfLines={1}>{title}</Text>
                    <Text style={styles.subtitle} numberOfLines={1}>
                        {selectedVoice ? `Read-aloud: ${selectedVoice.name}` : 'Powered by sign.mt'}
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

            {/* WebView area */}
            <View style={styles.webviewWrap}>
                <View style={styles.creditBadge} pointerEvents="none">
                    <Text style={styles.creditText}>avatar by sign.mt</Text>
                </View>
                {!hasContent ? (
                    <View style={styles.emptyState}>
                        <View style={styles.emptyIconBadge}>
                            <MaterialCommunityIcons name="hand-wave-outline" size={48} color="#432818" />
                        </View>
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
                            injectedJavaScriptBeforeContentLoaded={HIDE_CHROME_JS}
                            injectedJavaScript={HIDE_CHROME_JS}
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
                    <View style={styles.chatBox}>
                        <TextInput
                            style={styles.textInput}
                            value={inputText}
                            onChangeText={setInputText}
                            placeholder="Type something to sign…"
                            placeholderTextColor="#a09880"
                            returnKeyType="send"
                            onSubmitEditing={handleSend}
                        />
                        <TouchableOpacity
                            style={[styles.sendBtn, !inputText.trim() && styles.sendBtnDisabled]}
                            onPress={handleSend}
                            disabled={!inputText.trim()}
                        >
                            <MaterialIcons name="send" size={18} color="#FDF0D0" />
                        </TouchableOpacity>
                    </View>

                </View>
            </View>

            {/* Nav bar */}
            <View style={styles.navBar}>
                <TouchableOpacity style={styles.navItem} onPress={() => onNavigateTo('translate')}>
                    <Image
                        source={require('../assets/images/signly-logo.png')}
                        style={{ width: 18, height: 18, tintColor: '#817f74' }}
                        resizeMode="contain"
                    />
                    <Text style={styles.navLabelInactive}>Translate</Text>
                </TouchableOpacity>
                <View style={[styles.navItem, styles.navItemActive]}>
                    <MaterialCommunityIcons name="hand-wave" size={18} color="#FDF0D0" />
                    <Text style={styles.navLabelActive}>Animation</Text>
                </View>
                <TouchableOpacity style={styles.navItem} onPress={() => onNavigateTo('voice')}>
                    <MaterialCommunityIcons name="account-voice" size={18} color="#817f74" />
                    <Text style={styles.navLabelInactive}>Voice</Text>
                </TouchableOpacity>
            </View>

            <HistoryDrawer
                visible={drawerOpen}
                onClose={() => setDrawerOpen(false)}
                onOpenVoicePicker={() => setVoicePickerOpen(true)}
                pageType="animation"
                onSelectConversation={handleSelectConversation}
                onNewConversation={handleNewConversation}
            />
            <VoicePickerModal
                visible={voicePickerOpen}
                onClose={() => setVoicePickerOpen(false)}
            />
        </KeyboardAvoidingView>
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
    creditBadge: {
        position: 'absolute',
        bottom: 8,
        right: 10,
        zIndex: 10,
        paddingHorizontal: 7,
        paddingVertical: 3,
        borderRadius: 8,
        backgroundColor: 'rgba(255,255,255,0.72)',
    },
    creditText: {
        fontSize: 10,
        color: '#a09880',
    },
    emptyState: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
        gap: 16,
    },
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
    },
    inputRow: {
        width: '100%',
        flexDirection: 'row',
        alignItems: 'center',
        gap: 10,
    },
    chatBox: {
        flex: 1,
        height: 52,
        borderRadius: 26,
        backgroundColor: '#fff',
        borderWidth: 1,
        borderColor: '#e0d8cc',
        flexDirection: 'row',
        alignItems: 'center',
        paddingLeft: 18,
        paddingRight: 6,
    },
    textInput: {
        flex: 1,
        fontSize: 15,
        color: '#2c2c2e',
        paddingVertical: 0,
    },
    sendBtn: {
        width: 40,
        height: 40,
        borderRadius: 20,
        backgroundColor: '#432818',
        justifyContent: 'center',
        alignItems: 'center',
    },
    sendBtnDisabled: {
        opacity: 0.4,
    },
    // ── nav bar ──
    navBar: {
        width: '94%',
        marginBottom: 24,
        alignSelf: 'center',
        backgroundColor: 'rgba(255,255,255,0.55)',
        borderRadius: 50,
        paddingVertical: 12,
        paddingHorizontal: 10,
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
