import React, { useState } from 'react';
import type { ChatMessage } from '../../types';
import { UserMessage } from './UserMessage';
import { AssistantMessage } from './AssistantMessage';

interface ChatPanelProps {
  messages: ChatMessage[];
  isGenerating: boolean;
  canAsk: boolean;
  onSendMessage: (question: string) => void;
}

export const ChatPanel: React.FC<ChatPanelProps> = ({
  messages,
  isGenerating,
  canAsk,
  onSendMessage,
}) => {
  const [inputText, setInputText] = useState('');

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = () => {
    const trimmed = inputText.trim();
    if (!trimmed || isGenerating) return;
    onSendMessage(trimmed);
    setInputText('');
  };

  return (
    <div className="chat-panel-container">
      {/* Messages Scroll Area */}
      <div className="chat-messages-area">
        {messages.length === 0 ? (
          <div className="chat-empty-state">
            <div className="chat-empty-icon">💬</div>
            <h2 className="chat-empty-title">Start a conversation</h2>
            <p className="chat-empty-text">
              Upload documents using the sidebar and ask questions to search and receive grounded answers.
            </p>
          </div>
        ) : (
          messages.map((msg) =>
            msg.role === 'user' ? (
              <UserMessage
                key={msg.id}
                content={msg.content}
                timestamp={msg.timestamp}
              />
            ) : (
              <AssistantMessage
                key={msg.id}
                content={msg.content}
                timestamp={msg.timestamp}
                kind={msg.kind}
                isLoading={msg.isLoading}
                sources={msg.sources}
              />
            )
          )
        )}
      </div>

      {/* Input Bar */}
      <div className="chat-input-wrapper">
        <div className="chat-input-bar">
          <span style={{ fontSize: '1rem', color: '#565878' }}>📎</span>
          <input
            type="text"
            className="chat-input-field"
            placeholder={
              canAsk
                ? 'Ask a question about your uploaded documents...'
                : 'Upload documents to enable chat input'
            }
            disabled={!canAsk || isGenerating}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button
            type="button"
            className="chat-send-btn"
            disabled={!canAsk || !inputText.trim() || isGenerating}
            onClick={handleSend}
            title="Send Message"
          >
            ➤
          </button>
        </div>
        <p className="chat-hint">
          Press Enter to send • Shift + Enter for new line
        </p>
      </div>
    </div>
  );
};
