import { api } from './api';
import type { PipelineStatus, ProviderInfo } from '../types';
import type { ApiResponse } from './documentService';

export interface WorkspaceStatusResponseData {
  document_count: number;
  total_chunks: number;
  pipeline_status: PipelineStatus;
  provider_info: ProviderInfo;
  embedding_status: Record<string, string>;
}

export const workspaceService = {
  getStatus: async (): Promise<WorkspaceStatusResponseData> => {
    const res = await api.get<ApiResponse<WorkspaceStatusResponseData>>('/workspace/status');
    return res.data;
  },
};
