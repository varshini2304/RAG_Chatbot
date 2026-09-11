import React, { useState } from 'react';
import type { DocumentItem, PipelineStatus as PipelineStatusType, ChatSession } from '../../types';
import { DocumentList } from '../sidebar/DocumentList';
import { PipelineStatus } from '../sidebar/PipelineStatus';
import { SavedChats } from '../sidebar/SavedChats';

interface SidebarProps {
  username: string;
  documents: DocumentItem[];
  pipelineStatus: PipelineStatusType;
  savedSessions: ChatSession[];
  selectedDoc: string | null;
  offlineMode: boolean;
  onSelectDoc: (filename: string) => void;
  onDeleteDoc: (filename: string) => void;
  onClearWorkspace: () => void;
  onUploadFile: (file: File) => void;
  onSelectSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string) => void;
  onToggleOffline: (active: boolean) => void;
  onLogout: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  username,
  documents,
  pipelineStatus,
  savedSessions,
  selectedDoc,
  offlineMode,
  onSelectDoc,
  onDeleteDoc,
  onClearWorkspace,
  onUploadFile,
  onSelectSession,
  onDeleteSession,
  onToggleOffline,
  onLogout,
}) => {
  // Task 3: Documents HIDDEN by default
  const [showDocs, setShowDocs] = useState(false);
  const avatarLetter = username ? username[0].toUpperCase() : 'A';

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      onUploadFile(e.target.files[0]);
    }
  };

  return (
    <aside className="sidebar-container">
      {/* Task 4: Project Title / Branding at TOP of Sidebar */}
      <div className="sidebar-top-branding">
        <div className="hdr-logo">
          <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        </div>
        <div className="hdr-info">
          <p className="hdr-title" style={{ fontSize: '1.02rem', margin: 0 }}>
            Internal Document RAG Chatbot
          </p>
        </div>
      </div>

      {/* Sidebar Scroll Body (Middle) */}
      <div className="sidebar-body">
        {/* DOCUMENTS SECTION */}
        <div>
          <div className="section-label">Documents</div>

          {/* Upload Button */}
          <label className="upload-btn" style={{ cursor: 'pointer', marginBottom: '0.6rem' }}>
            <span>☁ Upload Documents</span>
            <input
              type="file"
              accept=".pdf,.txt,.png,.jpg,.jpeg,.webp,.tiff,.bmp"
              style={{ display: 'none' }}
              onChange={handleFileChange}
            />
          </label>

          {/* Show/Hide & Clear Workspace */}
          <div style={{ display: 'flex', gap: '0.4rem', marginBottom: '0.6rem' }}>
            <button
              type="button"
              className="saved-chat-btn"
              style={{ flex: 1, textAlign: 'center', fontSize: '0.72rem' }}
              onClick={() => setShowDocs(!showDocs)}
            >
              {showDocs ? '📂 Hide Documents' : '📂 View Documents'}
            </button>
            {documents.length > 0 && (
              <button
                type="button"
                className="saved-chat-btn"
                style={{ textAlign: 'center', fontSize: '0.72rem', color: '#f87171', borderColor: 'rgba(239,68,68,0.3)' }}
                onClick={onClearWorkspace}
                title="Clear all uploaded documents"
              >
                🗑️ Clear
              </button>
            )}
          </div>

          {showDocs && (
            <DocumentList
              documents={documents}
              selectedDoc={selectedDoc}
              onSelectDoc={onSelectDoc}
              onDeleteDoc={onDeleteDoc}
            />
          )}
        </div>

        {/* PIPELINE STATUS SECTION */}
        <div>
          <div className="section-label">Pipeline Status</div>
          <PipelineStatus status={pipelineStatus} />
        </div>

        {/* SAVED CHATS SECTION */}
        <div>
          <div className="section-label">Saved Chats</div>
          <SavedChats
            sessions={savedSessions}
            activeSessionId={null}
            onSelectSession={onSelectSession}
            onDeleteSession={onDeleteSession}
          />
        </div>

        {/* PRIVACY & SECURITY SECTION */}
        <div>
          <div className="section-label">Privacy & Security</div>
          <div
            style={{
              background: 'rgba(13, 14, 31, 0.7)',
              border: '1px solid var(--border)',
              borderRadius: '10px',
              padding: '0.6rem 0.8rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <span style={{ fontSize: '0.78rem', color: '#c7c9df', fontWeight: 500 }}>
              🔒 Offline Mode
            </span>
            <input
              type="checkbox"
              checked={offlineMode}
              onChange={(e) => onToggleOffline(e.target.checked)}
              style={{ accentColor: '#6366f1', width: '16px', height: '16px', cursor: 'pointer' }}
            />
          </div>
        </div>
      </div>

      {/* Task 6: Sidebar Footer (Bottom-Left User Profile & Logout) */}
      <div className="sidebar-footer">
        <div className="sidebar-user-profile">
          <div className="user-avatar">{avatarLetter}</div>
          <div className="user-info">
            <span className="user-name">{username || 'admin'}</span>
            <span className="user-role">User Profile</span>
          </div>
        </div>
        <button type="button" className="logout-btn" onClick={onLogout}>
          🚪 Logout
        </button>
      </div>
    </aside>
  );
};
