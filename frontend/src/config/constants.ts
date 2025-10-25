/**
 * Application Constants
 * Centralized configuration and magic strings
 */

export const APP_NAME = 'H1B Visa Community';

export const LOCAL_STORAGE_KEYS = {
  DARK_MODE: 'visa-dark-mode',
  SESSION_TOKEN: 'visa-session-token',
  ACTIVE_TAB: 'visa-active-tab',
} as const;

export const ROUTES = {
  TOPICS: 'topics',
  NEWS: 'news',
  COMMUNITY: 'community',
  AI: 'ai',
} as const;

export const AUTH_STEPS = {
  EMAIL: 'email',
  CODE: 'code',
  AUTHENTICATED: 'authenticated',
} as const;

export const AUTH_MODES = {
  LOGIN: 'login',
  SIGNUP: 'signup',
} as const;

export const VALIDATION = {
  EMAIL_REGEX: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  MIN_DISPLAY_NAME_LENGTH: 2,
  MAX_DISPLAY_NAME_LENGTH: 30,
  VERIFICATION_CODE_LENGTH: 6,
} as const;

export const UI_CONFIG = {
  AVATAR_SIZE: {
    SMALL: 40,
    LARGE: 64,
  },
  CODE_INPUT_FONT_SIZE: '1.5rem',
  CODE_INPUT_LETTER_SPACING: '0.5rem',
} as const;

export const API_CONFIG = {
  BASE_URL: (import.meta as any).env?.VITE_API_URL || '',
} as const;
