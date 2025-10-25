/**
 * AppLayout Component
 * Main layout wrapper with header and content area
 */

import { useState } from 'react';
import { Box, CssBaseline } from '@mui/material';
import { Header } from './Header';
import { AuthDialog } from '../features/auth';
import { useAuth } from '../contexts/AuthContext';
import { useLocalStorage } from '../hooks/useLocalStorage';
import { LOCAL_STORAGE_KEYS } from '../config/constants';

// Import existing page components
import TopicsHome from '../pages/TopicsHome';
import CommunityChat from '../CommunityChat';
import AINews from '../components/AINews';

export function AppLayout() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useLocalStorage<'topics' | 'news'>(
    LOCAL_STORAGE_KEYS.ACTIVE_TAB,
    'topics'
  );
  const [selectedTopic, setSelectedTopic] = useState<{ id: string; name: string } | null>(null);
  const [showAuthDialog, setShowAuthDialog] = useState(false);
  const [onlineCount, setOnlineCount] = useState(0);

  // Keep variable "used" for TypeScript
  console.debug('Online count:', onlineCount);

  const handleTopicSelect = (topicId: string, topicName: string) => {
    if (!user) {
      setShowAuthDialog(true);
    } else {
      setSelectedTopic({ id: topicId, name: topicName });
    }
  };

  const handleBackToTopics = () => {
    setSelectedTopic(null);
  };

  return (
    <>
      <CssBaseline />
      <Box sx={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
        {/* Header */}
        <Header activeTab={activeTab} onTabChange={setActiveTab} />

        {/* Content */}
        <Box
          sx={{
            flexGrow: 1,
            overflow: 'auto',
            WebkitOverflowScrolling: 'touch',
            minHeight: 0,
          }}
        >
          {activeTab === 'news' ? (
            <AINews onBackToTopics={() => setActiveTab('topics')} />
          ) : !selectedTopic ? (
            <TopicsHome onTopicSelect={handleTopicSelect} />
          ) : user ? (
            <CommunityChat
              userEmail={user.email}
              displayName={user.displayName}
              onOnlineCountChange={setOnlineCount}
              roomId={selectedTopic.id}
              roomName={selectedTopic.name}
              onBackToTopics={handleBackToTopics}
            />
          ) : null}
        </Box>

        {/* Auth Dialog */}
        <AuthDialog open={showAuthDialog} onClose={() => setShowAuthDialog(false)} />
      </Box>
    </>
  );
}
