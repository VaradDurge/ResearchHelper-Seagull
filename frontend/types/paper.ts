/**
 * # Paper Types
 * 
 * TypeScript types for papers, chunks, embeddings, and paper-related data structures.
 */
export interface Paper {
  id: string;
  title: string;
  authors: string[];
  abstract?: string;
  pdf_path?: string;
  pdf_url?: string;
  doi?: string;
  publication_date?: string;
  upload_date: string;
  workspace_id: string;
  user_id: string;
  status: PaperStatus;
  metadata?: Record<string, any>;
}

export enum PaperStatus {
  PROCESSING = "processing",
  READY = "ready",
  ERROR = "error",
}

export interface Chunk {
  id: string;
  paper_id: string;
  chunk_index: number;
  page_number: number;
  text: string;
  start_char: number;
  end_char: number;
  vector_id: string;
  metadata?: Record<string, any>;
}

export interface PaperListResponse {
  papers: Paper[];
  total: number;
}
