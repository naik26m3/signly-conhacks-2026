import { PermissionsGate } from '@/components/permissions-gate';
import { SessionProvider } from '@/contexts/SessionContext';
import { useState } from 'react';
import AnimationPage from './AnimationPage';
import TranslatePage from './TranslatePage';
import VoicePage from './VoicePage';

type Tab = 'translate' | 'animation' | 'voice';

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('translate');

  let page;
  if (activeTab === 'animation') {
    page = <AnimationPage onNavigateTo={setActiveTab} />;
  } else if (activeTab === 'voice') {
    page = <VoicePage onNavigateTo={setActiveTab} />;
  } else {
    page = <TranslatePage onNavigateTo={setActiveTab} />;
  }

  return (
    <SessionProvider>
      <PermissionsGate>{page}</PermissionsGate>
    </SessionProvider>
  );
}
