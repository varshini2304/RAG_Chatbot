import React from 'react';
import type { ChatMessage, DocumentItem } from '../types';
import { ChatPanel } from '../components/chat/ChatPanel';

interface ChatViewPageProps {
  messages: ChatMessage[];
  isGenerating: boolean;
  documents: DocumentItem[];
  onSendMessage: (question: string) => Promise<void>;
  onNewChat: () => void;
}

export const ChatViewPage: React.FC<ChatViewPageProps> = ({
  messages,
  isGenerating,
  documents,
  onSendMessage,
  onNewChat,
}) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '1rem' }}>
      {/* Top Banner */}
      <div
        className="sop-card"
        style={{
          padding: '0.75rem 1.25rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: 'var(--sop-bg-panel)',
          flexShrink: 0,
        }}
      >
        <div>
          <h2 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--sop-text-primary)', margin: 0 }}>
            RAG Knowledge Assistant
          </h2>
          <span style={{ fontSize: '0.72rem', color: 'var(--sop-text-secondary)' }}>
            Grounded question answering across {documents.length} ingested engineering documents
          </span>
        </div>

        <button
          type="button"
          className="sop-btn sop-btn-secondary"
          onClick={onNewChat}
          style={{ padding: '0.3rem 0.7rem', fontSize: '0.74rem' }}
        >
          + New Chat
        </button>
      </div>

      {/* Embedded Chat Panel */}
      <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        <ChatPanel
          messages={messages}
          isGenerating={isGenerating}
          canAsk={documents.length > 0}
          onSendMessage={onSendMessage}
        />
      </div>
    </div>
  );
};
