import React from 'react';
import type { DocumentItem, ProviderInfo } from '../../types';

interface HeaderProps {
  documents: DocumentItem[];
  totalChunks: number;
  retrievedCount: number;
  copyChatActive: boolean;
  canCopy: boolean;
  providerInfo: ProviderInfo;
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
  onNewChat: () => void;
  onCopyChat: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  documents,
  totalChunks,
  retrievedCount,
  copyChatActive,
  canCopy,
  providerInfo,
  sidebarOpen,
  onToggleSidebar,
  onNewChat,
  onCopyChat,
}) => {
  const isOffline = providerInfo.offline_mode || providerInfo.current_provider.toLowerCase() === 'ollama';
  const isUnavailable = providerInfo.current_provider === 'None';

  let aiClass = 'pill-green';
  let aiLabel = 'AI Provider';
  let aiValue = providerInfo.current_provider;
  let aiSubtext = <span style={{ color: '#81c784', fontWeight: 600 }}>Active</span>;
  let aiIconColor = '#81c784';

  if (isUnavailable) {
    aiClass = 'pill-red';
    aiLabel = 'AI Provider';
    aiValue = 'None';
    aiSubtext = <span style={{ color: '#f87171', fontWeight: 600 }}>Unavailable</span>;
    aiIconColor = '#f87171';
  } else if (isOffline) {
    aiClass = 'pill-gold';
    aiLabel = 'AI SLM';
    aiValue = providerInfo.current_provider;
    aiSubtext = <span style={{ color: '#fbbf24', fontWeight: 600 }}>Offline</span>;
    aiIconColor = '#fbbf24';
  }

  return (
    <div className="top-header-wrapper">
      <div className="top-header-row">
        <div className="top-header-bar">
          {/* Sidebar Toggle Button */}
          <button
            type="button"
            className="sidebar-toggle-btn"
            onClick={onToggleSidebar}
            title={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
            aria-label={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
              <line x1="9" y1="3" x2="9" y2="21"></line>
            </svg>
          </button>
          {providerInfo.offline_mode && (
            <span style={{ fontSize: '0.68rem', color: '#fbbf24', background: 'rgba(245,158,11,0.15)', border: '1px solid rgba(245,158,11,0.4)', padding: '1px 7px', borderRadius: '12px', marginLeft: '6px', fontWeight: 600 }}>
              🔒 Offline Mode
            </span>
          )}
        </div>

        <div className="hdr-actions">
          <button type="button" className="hdr-btn hdr-btn-primary" onClick={onNewChat}>
            ＋ New Chat
          </button>
          <button
            type="button"
            className="hdr-btn hdr-btn-secondary"
            onClick={onCopyChat}
            disabled={!canCopy}
            style={{ opacity: canCopy ? 1 : 0.5, cursor: canCopy ? 'pointer' : 'not-allowed' }}
          >
            {copyChatActive ? '✓ Copied' : '📋 Copy Chat'}
          </button>
        </div>
      </div>

      <div className="metrics-grid">
        {/* Metric 1: Documents */}
        <div className="hdr-pill">
          <div className="hdr-pill-icon pill-purple">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#b388ff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="16" y1="13" x2="8" y2="13"></line>
              <line x1="16" y1="17" x2="8" y2="17"></line>
            </svg>
          </div>
          <div className="hdr-pill-text">
            <span className="hdr-pill-label">Documents</span>
            <span className="hdr-pill-value">{documents.length}</span>
            <span className="hdr-pill-subtext">Files uploaded</span>
          </div>
        </div>

        {/* Metric 2: Chunks */}
        <div className="hdr-pill">
          <div className="hdr-pill-icon pill-orange">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#ffb74d" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
              <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
              <line x1="12" y1="22.08" x2="12" y2="12"></line>
            </svg>
          </div>
          <div className="hdr-pill-text">
            <span className="hdr-pill-label">Chunks</span>
            <span className="hdr-pill-value">{totalChunks}</span>
            <span className="hdr-pill-subtext">Total chunks</span>
          </div>
        </div>

        {/* Metric 3: Retrieved Chunks */}
        <div className="hdr-pill">
          <div className="hdr-pill-icon pill-blue">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#64b5f6" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
          </div>
          <div className="hdr-pill-text">
            <span className="hdr-pill-label">Retrieved Chunks</span>
            <span className="hdr-pill-value">{retrievedCount}</span>
            <span className="hdr-pill-subtext">For current query</span>
          </div>
        </div>

        {/* Metric 4: AI Provider */}
        <div className="hdr-pill">
          <div className={`hdr-pill-icon ${aiClass}`}>
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke={aiIconColor} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="11" width="18" height="10" rx="2"></rect>
              <circle cx="12" cy="5" r="2"></circle>
              <path d="M12 7v4"></path>
              <line x1="8" y1="16" x2="8" y2="16"></line>
              <line x1="16" y1="16" x2="16" y2="16"></line>
            </svg>
          </div>
          <div className="hdr-pill-text">
            <span className="hdr-pill-label">{aiLabel}</span>
            <span className="hdr-pill-value">{aiValue}</span>
            <span className="hdr-pill-subtext">{aiSubtext}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
