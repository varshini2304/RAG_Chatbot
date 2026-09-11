import React, { useEffect, useState } from 'react';
import type {
  DocumentItem,
  PipelineStatus as PipelineStatusType,
  ChatMessage,
  ProviderInfo,
} from '../types';
import { AppShell } from '../components/layout/AppShell';
import { WorkflowProvider } from '../context/WorkflowContext';
import { documentService } from '../services/documentService';
import { workspaceService } from '../services/workspaceService';
import { chatService } from '../services/chatService';
import { ApiError } from '../services/api';

interface DashboardPageProps {
  username: string;
  onLogout: () => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ username, onLogout }) => {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);

  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatusType>({
    text_extraction: false,
    chunking: false,
    embeddings: false,
    vector_store: false,
  });

  const [providerInfo, setProviderInfo] = useState<ProviderInfo>({
    current_provider: 'Gemini',
    current_model: 'gemini-2.5-flash',
    fallback_active: false,
    offline_mode: false,
  });

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  const [isGenerating, setIsGenerating] = useState(false);
  const [isUploading] = useState(false);

  // Load initial workspace state & documents on mount
  const refreshWorkspace = async () => {
    try {
      const docs = await documentService.listDocuments();
      setDocuments(docs);

      const statusRes = await workspaceService.getStatus();
      if (statusRes) {
        setPipelineStatus(statusRes.pipeline_status);
        setProviderInfo(statusRes.provider_info);
      }
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 401) {
        onLogout();
      } else {
        console.error('Failed to load workspace data:', err);
      }
    }
  };

  useEffect(() => {
    let isMounted = true;
    const initWorkspace = async () => {
      try {
        const docs = await documentService.listDocuments();
        if (isMounted) setDocuments(docs);

        const statusRes = await workspaceService.getStatus();
        if (isMounted && statusRes) {
          setPipelineStatus(statusRes.pipeline_status);
          setProviderInfo(statusRes.provider_info);
        }
      } catch (err: unknown) {
        if (isMounted) {
          if (err instanceof ApiError && err.status === 401) {
            onLogout();
          } else {
            console.error('Failed to load workspace data:', err);
          }
        }
      }
    };

    void initWorkspace();
    return () => {
      isMounted = false;
    };
  }, [onLogout]);

  const handleNewChat = () => {
    setMessages([]);
    setActiveSessionId(null);
  };

  const handleSendMessage = async (question: string) => {
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const userMsg: ChatMessage = {
      id: `m_${Date.now()}`,
      role: 'user',
      content: question,
      timestamp: timeStr,
    };

    const loadingMsg: ChatMessage = {
      id: `m_load_${Date.now()}`,
      role: 'assistant',
      content: 'Searching chunks & generating grounded response...',
      timestamp: timeStr,
      isLoading: true,
    };

    const updatedMessages = [...messages, userMsg, loadingMsg];
    setMessages(updatedMessages);
    setIsGenerating(true);

    let currentSession = activeSessionId;
    if (!currentSession) {
      currentSession = `session_${Date.now()}`;
      setActiveSessionId(currentSession);
    }

    try {
      const queryRes = await chatService.query(question, 'en', currentSession, providerInfo.offline_mode);
      await refreshWorkspace();

      const assistantMsg: ChatMessage = {
        id: `m_ans_${Date.now()}`,
        role: 'assistant',
        content: queryRes.answer,
        timestamp: timeStr,
        kind: queryRes.kind,
        sources: (queryRes.sources || []).map((s, idx) => ({
          content: s.content,
          source_file: s.source_file,
          page_number: s.page_number,
          chunk_id: s.chunk_id,
          document_type: s.document_type,
          rank: idx + 1,
        })),
      };

      const finalMessages = [...messages, userMsg, assistantMsg];
      setMessages(finalMessages);

      try {
        await chatService.saveSession(currentSession, finalMessages);
      } catch (saveErr) {
        console.warn('Failed to save session history:', saveErr);
      }
    } catch (err: unknown) {
      const errorStr = err instanceof ApiError ? err.message : 'An error occurred during answer generation.';
      const errorMsgItem: ChatMessage = {
        id: `m_err_${Date.now()}`,
        role: 'assistant',
        content: `⚠️ ${errorStr}`,
        timestamp: timeStr,
        kind: 'error',
      };
      setMessages([...messages, userMsg, errorMsgItem]);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <WorkflowProvider>
      <AppShell
        username={username}
        onLogout={onLogout}
        documents={documents}
        pipelineStatus={pipelineStatus}
        messages={messages}
        isGenerating={isGenerating || isUploading}
        onSendMessage={handleSendMessage}
        onNewChat={handleNewChat}
        onRefreshWorkspace={refreshWorkspace}
      />
    </WorkflowProvider>
  );
};
