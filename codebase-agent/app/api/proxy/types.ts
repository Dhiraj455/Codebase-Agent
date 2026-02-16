/**
 * Type definitions for API proxy routes
 */

export interface AnalyzeRequest {
  repo_url: string;
  store_name?: string;
}

export interface AnalyzeResponse {
  success: boolean;
  repo_name: string;
  analysis_id: string;
  file_count: number;
  architecture_summary: Record<string, unknown>;
  code_smells: Array<Record<string, unknown>>;
  refactoring_strategies: Array<Record<string, unknown>>;
  statistics: Record<string, unknown>;
}

export interface QuestionRequest {
  question: string;
  analysis_id?: string;
  repo_name?: string;
}

export interface QuestionResponse {
  answer: string;
  sources?: Array<{
    file: string;
    chunk_type: string;
    name: string;
    score: number;
    preview: string;
  }>;
}

export interface ApiError {
  error: boolean;
  detail: string;
  status_code?: number;
}
