import { useState, useEffect } from 'react';
import ConnectionSetup from './components/ConnectionSetup';
import ChatInterface from './components/ChatInterface';
import HistoryView from './components/HistoryView';
import { getConnectionFromStorage, saveConnectionToStorage, clearConnectionFromStorage } from './lib/utils';

function App() {
  const [connection, setConnection] = useState(null);
  const [view, setView] = useState('chat'); // 'chat' | 'history'
  const [questionToAsk, setQuestionToAsk] = useState('');

  useEffect(() => {
    // Try to restore connection from localStorage
    const stored = getConnectionFromStorage();
    if (stored) {
      setConnection(stored);
    }
  }, []);

  const handleConnected = (connectionId, alias, totalTables) => {
    const conn = { connectionId, alias, totalTables };
    setConnection(conn);
    saveConnectionToStorage(connectionId, alias);
  };

  const handleDisconnect = () => {
    if (confirm('Are you sure you want to disconnect? This will clear your session.')) {
      setConnection(null);
      clearConnectionFromStorage();
      setView('chat');
    }
  };

  const handleShowHistory = () => {
    setView('history');
  };

  const handleBackToChat = () => {
    setView('chat');
  };

  const handleSelectQuestion = (question) => {
    setQuestionToAsk(question);
  };

  if (!connection) {
    return <ConnectionSetup onConnected={handleConnected} />;
  }

  if (view === 'history') {
    return (
      <HistoryView
        onBack={handleBackToChat}
        onSelectQuestion={handleSelectQuestion}
      />
    );
  }

  return (
    <ChatInterface
      connectionId={connection.connectionId}
      alias={connection.alias}
      onDisconnect={handleDisconnect}
      onShowHistory={handleShowHistory}
      initialQuestion={questionToAsk}
    />
  );
}

export default App;
