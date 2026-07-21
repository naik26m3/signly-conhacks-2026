import { PageType } from '@/contexts/SessionContext';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Image, StyleSheet, Text, TouchableOpacity, View } from 'react-native';

type Props = {
    active: PageType;
    onNavigateTo: (page: PageType) => void;
};

const ACTIVE_TINT = '#FDF0D0';
const INACTIVE_TINT = '#817f74';

// Display order, left to right. Changing this array reorders the nav on every page.
const TABS: { key: PageType; label: string }[] = [
    { key: 'voice', label: 'Voice' },
    { key: 'animation', label: 'Animation' },
    { key: 'translate', label: 'Translate' },
];

function TabIcon({ page, tint }: { page: PageType; tint: string }) {
    if (page === 'translate') {
        return (
            <Image
                source={require('../assets/images/signly-logo.png')}
                style={{ width: 18, height: 18, tintColor: tint }}
                resizeMode="contain"
            />
        );
    }
    return (
        <MaterialCommunityIcons
            name={page === 'animation' ? 'hand-wave' : 'account-voice'}
            size={18}
            color={tint}
        />
    );
}

export function BottomNav({ active, onNavigateTo }: Props) {
    return (
        <View style={styles.navBar}>
            {TABS.map(({ key, label }) => {
                const isActive = key === active;
                const tint = isActive ? ACTIVE_TINT : INACTIVE_TINT;

                // The active tab renders as a plain View — tapping the page you're
                // already on is a no-op, so it shouldn't be a button.
                if (isActive) {
                    return (
                        <View
                            key={key}
                            style={[styles.navItem, styles.navItemActive]}
                            accessibilityRole="tab"
                            accessibilityState={{ selected: true }}
                            accessibilityLabel={`${label}, current page`}
                        >
                            <TabIcon page={key} tint={tint} />
                            <Text style={styles.navLabelActive}>{label}</Text>
                        </View>
                    );
                }

                return (
                    <TouchableOpacity
                        key={key}
                        style={styles.navItem}
                        onPress={() => onNavigateTo(key)}
                        accessibilityRole="tab"
                        accessibilityState={{ selected: false }}
                        accessibilityLabel={`Go to ${label}`}
                    >
                        <TabIcon page={key} tint={tint} />
                        <Text style={styles.navLabelInactive}>{label}</Text>
                    </TouchableOpacity>
                );
            })}
        </View>
    );
}

const styles = StyleSheet.create({
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
        color: INACTIVE_TINT,
        fontSize: 12,
        fontWeight: '700',
        marginTop: 6,
    },
    navLabelActive: {
        color: ACTIVE_TINT,
        fontSize: 12,
        fontWeight: '700',
        marginTop: 6,
    },
});
