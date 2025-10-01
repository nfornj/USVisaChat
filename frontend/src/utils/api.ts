import axios from 'axios';
import type {
  SearchRequest,
  SearchResponse,
  StatsResponse,
  HealthResponse,
  CategoriesResponse,
  ExamplesResponse,
} from '../types';

const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || '';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Authentication API
export const authAPI = {
  // Request verification code
  requestCode: async (email: string, displayName: string): Promise<{
    success: boolean;
    message: string;
    user_id?: number;
  }> => {
    const { data } = await api.post('/auth/request-code', {
      email,
      display_name: displayName,
    });
    return data;
  },

  // Verify code and login
  verifyCode: async (email: string, code: string): Promise<{
    success: boolean;
    message: string;
    session_token?: string;
    user?: {
      id: number;
      email: string;
      displayName: string;
      isVerified: boolean;
    };
  }> => {
    const { data } = await api.post('/auth/verify-code', {
      email,
      code,
    });
    
    // Transform snake_case to camelCase
    if (data.user) {
      data.user.displayName = data.user.display_name;
      data.user.isVerified = data.user.is_verified;
      delete data.user.display_name;
      delete data.user.is_verified;
    }
    
    return data;
  },

  // Logout
  logout: async (sessionToken: string): Promise<{
    success: boolean;
    message: string;
  }> => {
    const { data } = await api.post('/auth/logout', null, {
      params: { session_token: sessionToken },
    });
    return data;
  },

  // Verify session
  verifySession: async (sessionToken: string): Promise<{
    success: boolean;
    message?: string;
    user?: {
      id: number;
      email: string;
      displayName: string;
      isVerified: boolean;
    };
  }> => {
    const { data } = await api.get('/auth/verify-session', {
      params: { session_token: sessionToken },
    });
    
    // Transform snake_case to camelCase
    if (data.user) {
      data.user.displayName = data.user.display_name;
      data.user.isVerified = data.user.is_verified;
      delete data.user.display_name;
      delete data.user.is_verified;
    }
    
    return data;
  },

  // Update profile (display name)
  updateProfile: async (sessionToken: string, displayName: string): Promise<{
    success: boolean;
    message: string;
    user?: {
      id: number;
      email: string;
      displayName: string;
      isVerified: boolean;
    };
  }> => {
    const { data } = await api.post('/auth/update-profile', {
      session_token: sessionToken,
      display_name: displayName,
    });
    
    // Transform snake_case to camelCase
    if (data.user) {
      data.user.displayName = data.user.display_name;
      data.user.isVerified = data.user.is_verified;
      delete data.user.display_name;
      delete data.user.is_verified;
    }
    
    return data;
  },

  // Get auth stats
  stats: async (): Promise<{
    total_users: number;
    verified_users: number;
    active_sessions: number;
  }> => {
    const { data } = await api.get('/auth/stats');
    return data;
  },
};

// Search API
export const searchAPI = {
  // Health check
  health: async (): Promise<HealthResponse> => {
    const { data } = await api.get<HealthResponse>('/health');
    return data;
  },

  // Get statistics
  stats: async (): Promise<StatsResponse> => {
    const { data } = await api.get<StatsResponse>('/stats');
    return data;
  },

  // Search conversations
  search: async (request: SearchRequest): Promise<SearchResponse> => {
    const { data } = await api.post<SearchResponse>('/search', request);
    return data;
  },

  // Chat with synthesized responses
  chat: async (request: SearchRequest): Promise<any> => {
    const { data } = await api.post('/chat', request);
    return data;
  },

  // AI Assistant with RedBus2US knowledge
  askAI: async (request: SearchRequest): Promise<{
    query: string;
    answer: string;
    sources: Array<{
      title: string;
      url: string;
      date: string;
      relevance_score: number;
    }>;
    confidence: number;
    type: string;
    articles_found: number;
    processing_time_ms: number;
  }> => {
    const { data } = await api.post('/api/ai/ask', request);
    return data;
  },

  // Get available categories for filtering
  categories: async (): Promise<CategoriesResponse> => {
    const { data } = await api.get<CategoriesResponse>('/search/categories');
    return data;
  },

  // Get example queries
  examples: async (): Promise<ExamplesResponse> => {
    const { data } = await api.get<ExamplesResponse>('/search/examples');
    return data;
  },
};

export { authAPI as chatAPI };
export default api;
