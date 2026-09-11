import React, { useState } from 'react';
import { AppSidebar, type AppNavRoute } from './AppSidebar';
import { TopBar } from './TopBar';
import { WorkflowStepper } from './WorkflowStepper';
import { useSopWorkflow } from '../../context/WorkflowContext';
import type { WorkflowStageNumber } from '../../types/sop';

// Pages
import { VideoProcessingPage } from '../../pages/VideoProcessingPage';
import { WorkStepTimelinePage } from '../../pages/WorkStepTimelinePage';
import { WorkStepDetailPage } from '../../pages/WorkStepDetailPage';
import { ConflictResolutionPage } from '../../pages/ConflictResolutionPage';
import { ExpertReviewPage } from '../../pages/ExpertReviewPage';
import { SOPExportPage } from '../../pages/SOPExportPage';
import { ChatViewPage } from '../../pages/ChatViewPage';
import { DocumentsViewPage } from '../../pages/DocumentsViewPage';
import { SettingsPage } from '../../pages/SettingsPage';

// Types from RAG
import type { DocumentItem, PipelineStatus, ChatMessage } from '../../types';

interface AppShellProps {
  username: string;
  onLogout: () => void;
  // RAG props to maintain 100% functionality
  documents: DocumentItem[];
  pipelineStatus: PipelineStatus;
  messages: ChatMessage[];
  isGenerating: boolean;
  onSendMessage: (q: string) => Promise<void>;
  onNewChat: () => void;
  onRefreshWorkspace: () => Promise<void>;
}

export const AppShell: React.FC<AppShellProps> = ({
  username,
  onLogout,
  documents,
  pipelineStatus,
  messages,
  isGenerating,
  onSendMessage,
  onNewChat,
  onRefreshWorkspace,
}) => {
  const [currentRoute, setCurrentRoute] = useState<AppNavRoute>('video_processing');

  const {
    currentStage,
    setCurrentStage,
    video,
    activeDatasetType,
    switchDataset,
    hasUnresolvedConflicts,
    allStepsApproved,
    setSelectedStepId,
  } = useSopWorkflow();

  // Synchronize route and workflow stage
  const handleSelectWorkflowStage = (stage: WorkflowStageNumber) => {
    setCurrentStage(stage);
    switch (stage) {
      case 1:
        setCurrentRoute('video_processing');
        break;
      case 2:
        setCurrentRoute('timeline');
        break;
      case 3:
        setCurrentRoute('step_detail');
        break;
      case 4:
        setCurrentRoute('conflicts');
        break;
      case 5:
        setCurrentRoute('review');
        break;
      case 6:
        setCurrentRoute('export');
        break;
    }
  };

  const handleSidebarNavigate = (route: AppNavRoute) => {
    setCurrentRoute(route);
    switch (route) {
      case 'video_processing':
        setCurrentStage(1);
        break;
      case 'timeline':
        setCurrentStage(2);
        break;
      case 'step_detail':
        setCurrentStage(3);
        break;
      case 'conflicts':
        setCurrentStage(4);
        break;
      case 'review':
        setCurrentStage(5);
        break;
      case 'export':
        setCurrentStage(6);
        break;
    }
  };

  const getPageTitle = (): { title: string; breadcrumb: string[] } => {
    switch (currentRoute) {
      case 'video_processing':
        return { title: 'Video Processing & Ingestion', breadcrumb: ['Workflow', 'Video Processing'] };
      case 'timeline':
        return { title: 'Work-Step Timeline & Multimodal Review', breadcrumb: ['Workflow', 'Timeline'] };
      case 'step_detail':
        return { title: 'Structured Step Detail & Evidence Traceability', breadcrumb: ['Workflow', 'Work Steps', 'Detail'] };
      case 'conflicts':
        return { title: 'Conflict Detection & Manual Comparison', breadcrumb: ['Workflow', 'Conflict Resolution'] };
      case 'review':
        return { title: 'Expert Human Review & Quality Gate', breadcrumb: ['Workflow', 'Expert Review'] };
      case 'export':
        return { title: 'Standard Operating Procedure (SOP) Export', breadcrumb: ['Workflow', 'Bilingual SOP Export'] };
      case 'chat':
        return { title: 'RAG Knowledge Assistant & Q&A', breadcrumb: ['Knowledge Hub', 'RAG Chat'] };
      case 'documents':
        return { title: 'Workspace Document Repository', breadcrumb: ['Knowledge Hub', 'Documents'] };
      case 'settings':
        return { title: 'System Runtime Settings', breadcrumb: ['System', 'Settings'] };
    }
  };

  const { title, breadcrumb } = getPageTitle();
  const isWorkflowRoute = ['video_processing', 'timeline', 'step_detail', 'conflicts', 'review', 'export'].includes(currentRoute);

  return (
    <div className="sop-app-container">
      {/* Persistent Left Sidebar */}
      <AppSidebar
        currentRoute={currentRoute}
        onNavigate={handleSidebarNavigate}
        username={username}
        onLogout={onLogout}
        hasConflicts={hasUnresolvedConflicts}
      />

      {/* Main Content Area */}
      <div className="sop-main-area">
        {/* Global Top Bar */}
        <TopBar
          title={title}
          breadcrumb={breadcrumb}
          video={isWorkflowRoute ? video : undefined}
          activeDatasetType={activeDatasetType}
          onSwitchDataset={switchDataset}
          username={username}
        />

        {/* Global 6-Phase Linear Workflow Stepper (Always visible on workflow pages) */}
        {isWorkflowRoute && (
          <WorkflowStepper
            currentStage={currentStage}
            onSelectStage={handleSelectWorkflowStage}
            hasConflicts={hasUnresolvedConflicts}
            allApproved={allStepsApproved}
          />
        )}

        {/* Viewport for active route */}
        <main className="sop-content-viewport">
          {currentRoute === 'video_processing' && (
            <VideoProcessingPage
              onProceedToTimeline={() => handleSelectWorkflowStage(2)}
            />
          )}

          {currentRoute === 'timeline' && (
            <WorkStepTimelinePage
              onInspectStep={(stepId) => {
                setSelectedStepId(stepId);
                handleSelectWorkflowStage(3);
              }}
            />
          )}

          {currentRoute === 'step_detail' && (
            <WorkStepDetailPage
              onBackToTimeline={() => handleSelectWorkflowStage(2)}
              onProceedToConflicts={() => handleSelectWorkflowStage(4)}
            />
          )}

          {currentRoute === 'conflicts' && (
            <ConflictResolutionPage
              onProceedToReview={() => handleSelectWorkflowStage(5)}
            />
          )}

          {currentRoute === 'review' && (
            <ExpertReviewPage
              onGoToExport={() => handleSelectWorkflowStage(6)}
            />
          )}

          {currentRoute === 'export' && (
            <SOPExportPage />
          )}

          {currentRoute === 'chat' && (
            <ChatViewPage
              messages={messages}
              isGenerating={isGenerating}
              documents={documents}
              onSendMessage={onSendMessage}
              onNewChat={onNewChat}
            />
          )}

          {currentRoute === 'documents' && (
            <DocumentsViewPage
              documents={documents}
              pipelineStatus={pipelineStatus}
              onRefreshWorkspace={onRefreshWorkspace}
              onNavigateToChat={() => setCurrentRoute('chat')}
            />
          )}

          {currentRoute === 'settings' && (
            <SettingsPage />
          )}
        </main>
      </div>
    </div>
  );
};
