export interface DocumentItem {
  source_file: string;
  document_type: 'pdf' | 'txt' | string;
  chunk_count: number;
  embedding_status: 'completed' | 'pending' | 'failed';
  error_message?: string;
}

export interface SourceReference {
  content: string;
  source_file: string;
  page_number: number;
  chunk_id: string;
  document_type: string;
  rank?: number;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  sources?: SourceReference[];
  kind?: 'success' | 'message' | 'error' | 'insufficient_information';
  isLoading?: boolean;
}

export interface ChatSession {
  session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  chat_history: ChatMessage[];
}

export interface PipelineStatus {
  text_extraction: boolean;
  chunking: boolean;
  embeddings: boolean;
  vector_store: boolean;
}

export interface ProviderInfo {
  current_provider: string;
  current_model: string;
  fallback_active: boolean;
  offline_mode: boolean;
}

export * from './sop';
