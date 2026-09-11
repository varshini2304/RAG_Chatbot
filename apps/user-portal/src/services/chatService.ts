import { api } from './api';
import type { ChatMessage, ChatSession } from '../types';
import type { ApiResponse } from './documentService';

export interface ChatQueryRequestPayload {
  question: string;
  query_language?: string;
  session_id?: string | null;
  offline_mode?: boolean;
}

export interface SourceReferenceResponseData {
  content: string;
  source_file: string;
  page_number: number;
  chunk_id: string;
  document_type: string;
}

export interface ChatQueryResponseData {
  success: boolean;
  answer: string;
  kind: 'success' | 'insufficient_information' | 'error';
  retrieved_chunk_count: number;
  sources: SourceReferenceResponseData[];
  session_id?: string | null;
}

export interface ChatSessionSummaryData {
  session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatSessionDetailData extends ChatSessionSummaryData {
  chat_history: Array<{
    role: 'user' | 'assistant';
    content: string;
    timestamp?: string | null;
    sources?: SourceReferenceResponseData[];
  }>;
}

export const chatService = {
  query: async (
    question: string,
    queryLanguage = 'en',
    sessionId?: string | null,
    offlineMode?: boolean
  ): Promise<ChatQueryResponseData> => {
    const payload: ChatQueryRequestPayload = {
      question,
      query_language: queryLanguage,
      session_id: sessionId || null,
      offline_mode: offlineMode,
    };
    const res = await api.post<ApiResponse<ChatQueryResponseData>>('/chat/query', payload);
    return res.data;
  },

  listSessions: async (): Promise<ChatSessionSummaryData[]> => {
    const res = await api.get<ApiResponse<ChatSessionSummaryData[]>>('/chat/sessions');
    return res.data || [];
  },

  getSession: async (sessionId: string): Promise<ChatSession> => {
    const res = await api.get<ApiResponse<ChatSessionDetailData>>(`/chat/sessions/${encodeURIComponent(sessionId)}`);
    const data = res.data;

    const history: ChatMessage[] = data.chat_history.map((msg, index) => ({
      id: `msg_${sessionId}_${index}`,
      role: msg.role,
      content: msg.content,
      timestamp: msg.timestamp || '',
      sources: (msg.sources || []).map((s, idx) => ({
        content: s.content,
        source_file: s.source_file,
        page_number: s.page_number,
        chunk_id: s.chunk_id,
        document_type: s.document_type,
        rank: idx + 1,
      })),
    }));

    return {
      session_id: data.session_id,
      title: data.title,
      created_at: data.created_at,
      updated_at: data.updated_at,
      chat_history: history,
    };
  },

  saveSession: async (
    sessionId: string,
    messages: ChatMessage[]
  ): Promise<ChatSessionSummaryData> => {
    const payload = {
      session_id: sessionId,
      chat_history: messages.map((m) => ({
        role: m.role,
        content: m.content,
        timestamp: m.timestamp,
        sources: (m.sources || []).map((s) => ({
          content: s.content,
          source_file: s.source_file,
          page_number: s.page_number,
          chunk_id: s.chunk_id,
          document_type: s.document_type,
        })),
      })),
    };
    const res = await api.post<ApiResponse<ChatSessionSummaryData>>('/chat/sessions', payload);
    return res.data;
  },

  deleteSession: async (sessionId: string): Promise<void> => {
    await api.delete<ApiResponse<unknown>>(`/chat/sessions/${encodeURIComponent(sessionId)}`);
  },
};
