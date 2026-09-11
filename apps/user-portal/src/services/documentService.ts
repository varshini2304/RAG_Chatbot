import { api } from './api';
import type { DocumentItem } from '../types';

export interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T;
  errors?: string[];
}

export interface WorkspaceResponseData {
  documents: Array<{
    filename: string;
    document_type: string;
    chunk_count: number;
    embedding_status: 'completed' | 'pending' | 'failed';
  }>;
  total_documents: number;
  total_chunks: number;
}

export interface UploadDocumentResponseData {
  success: boolean;
  filename: string;
  chunk_count: number;
  embedding_status: string;
  message: string;
}

export interface DeleteDocumentResponseData {
  success: boolean;
  filename: string;
  message: string;
}

export interface ClearWorkspaceResponseData {
  success: boolean;
  message: string;
}

export const documentService = {
  listDocuments: async (): Promise<DocumentItem[]> => {
    const res = await api.get<ApiResponse<WorkspaceResponseData>>('/documents');
    if (res && res.data && Array.isArray(res.data.documents)) {
      return res.data.documents.map((d) => ({
        source_file: d.filename,
        document_type: d.document_type,
        chunk_count: d.chunk_count,
        embedding_status: d.embedding_status,
      }));
    }
    return [];
  },

  uploadDocument: async (file: File): Promise<UploadDocumentResponseData> => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await api.post<ApiResponse<UploadDocumentResponseData>>('/documents/upload', formData);
    return res.data;
  },

  deleteDocument: async (filename: string): Promise<DeleteDocumentResponseData> => {
    const res = await api.delete<ApiResponse<DeleteDocumentResponseData>>(`/documents/${encodeURIComponent(filename)}`);
    return res.data;
  },

  clearWorkspace: async (): Promise<ClearWorkspaceResponseData> => {
    const res = await api.delete<ApiResponse<ClearWorkspaceResponseData>>('/documents/workspace');
    return res.data;
  },
};
