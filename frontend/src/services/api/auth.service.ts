/**
 * Authentication API Service
 * Handles all authentication-related API calls
 */

import axios from 'axios';
import { API_CONFIG } from '../../config/constants';

const api = axios.create({
  baseURL: API_CONFIG.BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface UserProfile {
  id: number;
  email: string;
  displayName: string;
  isVerified: boolean;
}

export interface AuthResponse {
  success: boolean;
  message: string;
  session_token?: string;
  user?: UserProfile;
  user_id?: number;
}

// Transform snake_case API response to camelCase
const transformUser = (data: any) => {
  if (data.user) {
    data.user.displayName = data.user.display_name;
    data.user.isVerified = data.user.is_verified;
    delete data.user.display_name;
    delete data.user.is_verified;
  }
  return data;
};

export const authService = {
  /**
   * Request verification code via email
   */
  async requestCode(email: string, displayName: string): Promise<AuthResponse> {
    const { data } = await api.post('/auth/request-code', {
      email,
      display_name: displayName,
    });
    return data;
  },

  /**
   * Verify code and login
   */
  async verifyCode(email: string, code: string): Promise<AuthResponse> {
    const { data } = await api.post('/auth/verify-code', { email, code });
    return transformUser(data);
  },

  /**
   * Logout user
   */
  async logout(sessionToken: string): Promise<AuthResponse> {
    const { data } = await api.post('/auth/logout', null, {
      params: { session_token: sessionToken },
    });
    return data;
  },

  /**
   * Verify if session is still valid
   */
  async verifySession(sessionToken: string): Promise<AuthResponse> {
    const { data } = await api.get('/auth/verify-session', {
      params: { session_token: sessionToken },
    });
    return transformUser(data);
  },

  /**
   * Update user profile (display name)
   */
  async updateProfile(sessionToken: string, displayName: string): Promise<AuthResponse> {
    const { data } = await api.post('/auth/update-profile', {
      session_token: sessionToken,
      display_name: displayName,
    });
    return transformUser(data);
  },

  /**
   * Get authentication statistics
   */
  async getStats(): Promise<{
    total_users: number;
    verified_users: number;
    active_sessions: number;
  }> {
    const { data } = await api.get('/auth/stats');
    return data;
  },
};
