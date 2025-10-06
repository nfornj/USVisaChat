export interface SearchResult {
  id: string;
  score: number;
  text: string;
  metadata: {
    text: string;
    source_file: string;
    message_id: string;
    user_id: string;
    timestamp: string;
    chat_id: string;
    primary_category: string;
    visa_type: string;
    location: string;
    is_question: boolean;
    question_confidence: number;
    text_length: number;
    created_at: string;
  };
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total_found: number;
  processing_time_ms: number;
}

export interface StatsResponse {
  collection_name: string;
  total_vectors: number;
  status: string;
  vector_dimensions: number;
  embedding_model: string;
}

export interface HealthResponse {
  status: string;
  message: string;
  version: string;
}

export interface SearchFilters {
  visa_type?: string;
  primary_category?: string;
  location?: string;
  is_question?: boolean;
}

export interface SearchRequest {
  query: string;
  filters?: SearchFilters;
  limit?: number;
}

export interface CategoriesResponse {
  visa_types: string[];
  categories: string[];
  locations: string[];
}

export interface SearchExample {
  query: string;
  description: string;
}

export interface ExamplesResponse {
  examples: SearchExample[];
}








