import React from 'react';
import type { ChatSession } from '../../types';

interface SavedChatsProps {
  sessions: ChatSession[];
  activeSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string) => void;
}

export const SavedChats: React.FC<SavedChatsProps> = ({
  sessions,
  onSelectSession,
  onDeleteSession,
}) => {
  if (sessions.length === 0) {
    return (
      <div style={{ padding: '0.4rem 0.2rem', color: 'var(--muted)', fontSize: '0.78rem' }}>
        No saved chats yet.
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
      {sessions.map((session) => (
        <div key={session.session_id} className="saved-chat-item">
          <button
            type="button"
            className="saved-chat-btn"
            onClick={() => onSelectSession(session.session_id)}
          >
            💬 {session.title}
          </button>
          <button
            type="button"
            className="sb-doc-del-btn"
            title="Delete this chat"
            onClick={() => onDeleteSession(session.session_id)}
          >
            🗑️
          </button>
        </div>
      ))}
    </div>
  );
};
