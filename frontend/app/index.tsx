import { useState } from 'react';
import TranslatePage from './TranslatePage';
import AnimationPage from './AnimationPage';

type Tab = 'translate' | 'animation';

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('translate');

  if (activeTab === 'animation') {
    return <AnimationPage onNavigateTo={setActiveTab} />;
  }
  return <TranslatePage onNavigateTo={setActiveTab} />;
}
