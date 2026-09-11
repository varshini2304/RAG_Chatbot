import React from 'react';

interface UserMessageProps {
  content: string;
  timestamp: string;
}

export const UserMessage: React.FC<UserMessageProps> = ({ content, timestamp }) => {
  return (
    <div className="chat-turn chat-turn-user">
      <div className="chat-message chat-message-user">
        <div className="chat-message-inner">
          <div className="chat-avatar chat-avatar-user">👤</div>
          <div className="chat-message-body">
            <div className="chat-message-top">
              <div className="chat-message-meta">
                <span className="chat-name">You</span>
                <span className="chat-time">{timestamp}</span>
              </div>
            </div>
            <p className="chat-message-text">{content}</p>
          </div>
        </div>
      </div>
    </div>
  );
};
