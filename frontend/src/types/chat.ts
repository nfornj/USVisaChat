export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sources?: any[];  // Can be SearchResult[] or RedBus2US sources
  isStreaming?: boolean;
}

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
}

export interface SearchResult {
  id: string;
  score: number;
  text: string;
  metadata: {
    visa_type: string;
    primary_category: string;
    location: string;
    timestamp: string;
  };
}

export interface ChatRequest {
  message: string;
  conversationId?: string;
  includeHistory?: boolean;
}

export interface ChatResponse {
  message: string;
  sources: SearchResult[];
  conversationId: string;
  processingTimeMs: number;
}





