import React from 'react';

export type AppNavRoute =
  | 'video_processing'
  | 'timeline'
  | 'step_detail'
  | 'conflicts'
  | 'review'
  | 'export'
  | 'chat'
  | 'documents'
  | 'settings';

interface AppSidebarProps {
  currentRoute: AppNavRoute;
  onNavigate: (route: AppNavRoute) => void;
  username: string;
  onLogout: () => void;
  hasConflicts?: boolean;
}

export const AppSidebar: React.FC<AppSidebarProps> = ({
  currentRoute,
  onNavigate,
  username,
  onLogout,
  hasConflicts,
}) => {
  return (
    <aside className="sop-sidebar">
      {/* Brand Header */}
      <div className="sop-brand">
        <div className="sop-brand-badge">SOP</div>
        <div className="sop-brand-text">
          <h1>RAG SOP</h1>
          <p>Manufacturing Knowledge System</p>
        </div>
      </div>

      {/* Nav List */}
      <nav aria-label="Main Navigation" className="sop-nav-scroll">
        {/* Workflow Group */}
        <div>
          <div className="sop-nav-group-title">SOP Workflow Pipeline</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <button
              type="button"
              className={`sop-nav-item ${currentRoute === 'video_processing' ? 'active' : ''}`}
              onClick={() => onNavigate('video_processing')}
            >
              <span className="sop-nav-icon">🎬</span>
              <span>1. Video Processing</span>
            </button>

            <button
              type="button"
              className={`sop-nav-item ${currentRoute === 'timeline' ? 'active' : ''}`}
              onClick={() => onNavigate('timeline')}
            >
              <span className="sop-nav-icon">⏱</span>
              <span>2. Step Timeline</span>
            </button>

            <button
              type="button"
              className={`sop-nav-item ${currentRoute === 'step_detail' ? 'active' : ''}`}
              onClick={() => onNavigate('step_detail')}
            >
              <span className="sop-nav-icon">🔍</span>
              <span>3. Step Detail</span>
            </button>

            <button
              type="button"
              className={`sop-nav-item ${currentRoute === 'conflicts' ? 'active' : ''}`}
              onClick={() => onNavigate('conflicts')}
            >
              <span className="sop-nav-icon">⚠</span>
              <span>4. Conflict Resolution</span>
              {hasConflicts && (
                <span style={{ marginLeft: 'auto', backgroundColor: 'var(--sop-red)', color: '#fff', fontSize: '0.65rem', borderRadius: '10px', padding: '1px 5px', fontWeight: 700 }}>
                  1
                </span>
              )}
            </button>

            <button
              type="button"
              className={`sop-nav-item ${currentRoute === 'review' ? 'active' : ''}`}
              onClick={() => onNavigate('review')}
            >
              <span className="sop-nav-icon">📋</span>
              <span>5. Expert Review</span>
            </button>

            <button
              type="button"
              className={`sop-nav-item ${currentRoute === 'export' ? 'active' : ''}`}
              onClick={() => onNavigate('export')}
            >
              <span className="sop-nav-icon">📑</span>
              <span>6. Final Bilingual SOP</span>
            </button>
          </div>
        </div>

        {/* Knowledge Hub Group (Preserved RAG Chat & Documents) */}
        <div>
          <div className="sop-nav-group-title">Knowledge Hub</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <button
              type="button"
              className={`sop-nav-item ${currentRoute === 'chat' ? 'active' : ''}`}
              onClick={() => onNavigate('chat')}
            >
              <span className="sop-nav-icon">💬</span>
              <span>RAG Chat & Q&A</span>
            </button>

            <button
              type="button"
              className={`sop-nav-item ${currentRoute === 'documents' ? 'active' : ''}`}
              onClick={() => onNavigate('documents')}
            >
              <span className="sop-nav-icon">📂</span>
              <span>Workspace Documents</span>
            </button>
          </div>
        </div>

        {/* System Group */}
        <div>
          <div className="sop-nav-group-title">System</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <button
              type="button"
              className={`sop-nav-item ${currentRoute === 'settings' ? 'active' : ''}`}
              onClick={() => onNavigate('settings')}
            >
              <span className="sop-nav-icon">⚙</span>
              <span>Runtime Settings</span>
            </button>
          </div>
        </div>
      </nav>

      {/* Sidebar Footer */}
      <div className="sop-sidebar-footer">
        <div className="sop-user-info">
          <div className="sop-avatar">
            {username.slice(0, 2).toUpperCase()}
          </div>
          <div>
            <div className="sop-user-name">{username}</div>
            <div className="sop-user-role">Manufacturing Team</div>
          </div>
        </div>

        <button
          type="button"
          className="sop-logout-btn"
          onClick={onLogout}
          title="Sign out of user portal"
        >
          ⏻
        </button>
      </div>
    </aside>
  );
};
