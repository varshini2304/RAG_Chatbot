import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import type { SourceReference } from '../../types';
import { SourceReferences } from './SourceReferences';

interface AssistantMessageProps {
  content: string;
  timestamp: string;
  kind?: 'success' | 'message' | 'error' | 'insufficient_information';
  isLoading?: boolean;
  sources?: SourceReference[];
}

export const AssistantMessage: React.FC<AssistantMessageProps> = ({
  content,
  timestamp,
  kind = 'message',
  isLoading = false,
  sources = [],
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="chat-turn chat-turn-assistant">
      <div className="chat-message chat-message-assistant">
        <div className="chat-message-inner">
          <div className="chat-avatar chat-avatar-assistant">✨</div>
          <div className="chat-message-body">
            <div className="chat-message-top">
              <div className="chat-message-meta">
                <span className="chat-name">Assistant</span>
                <span className="chat-time">{timestamp}</span>
              </div>
              {!isLoading && content && (
                <button
                  type="button"
                  onClick={handleCopy}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#8b8ea9',
                    fontSize: '0.74rem',
                    cursor: 'pointer',
                  }}
                  title="Copy response"
                >
                  {copied ? '✓ Copied' : '📋 Copy'}
                </button>
              )}
            </div>

            {isLoading ? (
              <span className="loading-dots">Searching chunks & generating grounded response...</span>
            ) : (
              <div className={`chat-message-text ${kind === 'error' ? 'chat-error' : ''}`}>
                {kind === 'error' ? (
                  content
                ) : (
                  <ReactMarkdown>{content}</ReactMarkdown>
                )}
              </div>
            )}

            {!isLoading && sources.length > 0 && (
              <SourceReferences sources={sources} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
