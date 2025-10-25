/**
 * Auth Context
 * Manages authentication state, user session, and auth operations
 */

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { authService, UserProfile } from '../services/api/auth.service';
import { LOCAL_STORAGE_KEYS, AUTH_STEPS, AUTH_MODES, VALIDATION } from '../config/constants';

type AuthStep = typeof AUTH_STEPS[keyof typeof AUTH_STEPS];
type AuthMode = typeof AUTH_MODES[keyof typeof AUTH_MODES];

interface AuthContextType {
  // State
  user: UserProfile | null;
  authStep: AuthStep;
  authMode: AuthMode;
  email: string;
  displayName: string;
  code: string;
  loading: boolean;
  error: string;
  successMessage: string;
  
  // Actions
  setAuthStep: (step: AuthStep) => void;
  setAuthMode: (mode: AuthMode) => void;
  setEmail: (email: string) => void;
  setDisplayName: (name: string) => void;
  setCode: (code: string) => void;
  setError: (error: string) => void;
  setSuccessMessage: (message: string) => void;
  
  // Operations
  requestCode: () => Promise<boolean>;
  verifyCode: () => Promise<boolean>;
  logout: () => Promise<void>;
  updateProfile: (newDisplayName: string) => Promise<boolean>;
  
  // Utilities
  clearError: () => void;
  backToEmail: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [authStep, setAuthStep] = useState<AuthStep>(AUTH_STEPS.EMAIL);
  const [authMode, setAuthMode] = useState<AuthMode>(AUTH_MODES.LOGIN);
  const [email, setEmail] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  // Check for existing session on mount
  useEffect(() => {
    const checkSession = async () => {
      const sessionToken = localStorage.getItem(LOCAL_STORAGE_KEYS.SESSION_TOKEN);
      if (sessionToken) {
        try {
          const response = await authService.verifySession(sessionToken);
          if (response.success && response.user) {
            setUser(response.user);
            setAuthStep(AUTH_STEPS.AUTHENTICATED);
          } else {
            localStorage.removeItem(LOCAL_STORAGE_KEYS.SESSION_TOKEN);
          }
        } catch (err) {
          console.error('Session verification failed:', err);
          localStorage.removeItem(LOCAL_STORAGE_KEYS.SESSION_TOKEN);
        }
      }
    };

    checkSession();
  }, []);

  const requestCode = async (): Promise<boolean> => {
    setError('');
    setSuccessMessage('');

    // Validation
    if (!email || !VALIDATION.EMAIL_REGEX.test(email.trim())) {
      setError('Please enter a valid email address');
      return false;
    }

    if (authMode === AUTH_MODES.SIGNUP) {
      if (!displayName || displayName.trim().length < VALIDATION.MIN_DISPLAY_NAME_LENGTH) {
        setError(`Please enter a display name (at least ${VALIDATION.MIN_DISPLAY_NAME_LENGTH} characters)`);
        return false;
      }

      if (displayName.trim().length > VALIDATION.MAX_DISPLAY_NAME_LENGTH) {
        setError(`Display name must be ${VALIDATION.MAX_DISPLAY_NAME_LENGTH} characters or less`);
        return false;
      }
    }

    setLoading(true);

    try {
      const nameToUse = authMode === AUTH_MODES.SIGNUP 
        ? displayName.trim() 
        : email.trim().split('@')[0];

      const response = await authService.requestCode(
        email.trim().toLowerCase(),
        nameToUse
      );

      if (response.success) {
        setSuccessMessage(response.message);
        setAuthStep(AUTH_STEPS.CODE);
        return true;
      } else {
        setError('Failed to send verification code. Please try again.');
        return false;
      }
    } catch (err) {
      setError('Failed to send verification code. Please try again.');
      console.error('Request code error:', err);
      return false;
    } finally {
      setLoading(false);
    }
  };

  const verifyCode = async (): Promise<boolean> => {
    setError('');
    setSuccessMessage('');

    if (!code || code.trim().length !== VALIDATION.VERIFICATION_CODE_LENGTH) {
      setError(`Please enter a valid ${VALIDATION.VERIFICATION_CODE_LENGTH}-digit code`);
      return false;
    }

    setLoading(true);

    try {
      const response = await authService.verifyCode(
        email.trim().toLowerCase(),
        code.trim()
      );

      if (response.success && response.session_token && response.user) {
        localStorage.setItem(LOCAL_STORAGE_KEYS.SESSION_TOKEN, response.session_token);
        setUser(response.user);
        setAuthStep(AUTH_STEPS.AUTHENTICATED);
        setSuccessMessage('Successfully logged in!');
        return true;
      } else {
        setError(response.message || 'Invalid verification code');
        return false;
      }
    } catch (err) {
      setError('Failed to verify code. Please try again.');
      console.error('Verify code error:', err);
      return false;
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    const sessionToken = localStorage.getItem(LOCAL_STORAGE_KEYS.SESSION_TOKEN);
    if (sessionToken) {
      try {
        await authService.logout(sessionToken);
      } catch (err) {
        console.error('Logout error:', err);
      }
    }

    localStorage.removeItem(LOCAL_STORAGE_KEYS.SESSION_TOKEN);
    setUser(null);
    setAuthStep(AUTH_STEPS.EMAIL);
    setEmail('');
    setDisplayName('');
    setCode('');
    setError('');
    setSuccessMessage('');
  };

  const updateProfile = async (newDisplayName: string): Promise<boolean> => {
    if (!newDisplayName || newDisplayName.trim().length < VALIDATION.MIN_DISPLAY_NAME_LENGTH) {
      setError(`Display name must be at least ${VALIDATION.MIN_DISPLAY_NAME_LENGTH} characters`);
      return false;
    }

    if (newDisplayName.trim().length > VALIDATION.MAX_DISPLAY_NAME_LENGTH) {
      setError(`Display name must be ${VALIDATION.MAX_DISPLAY_NAME_LENGTH} characters or less`);
      return false;
    }

    setLoading(true);

    try {
      const sessionToken = localStorage.getItem(LOCAL_STORAGE_KEYS.SESSION_TOKEN);
      if (!sessionToken) {
        setError('Session expired. Please login again.');
        return false;
      }

      const response = await authService.updateProfile(sessionToken, newDisplayName.trim());

      if (response.success && response.user) {
        setUser(response.user);
        setSuccessMessage('Profile updated successfully!');
        return true;
      } else {
        setError(response.message || 'Failed to update profile');
        return false;
      }
    } catch (err) {
      setError('Failed to update profile. Please try again.');
      console.error('Profile update error:', err);
      return false;
    } finally {
      setLoading(false);
    }
  };

  const clearError = () => {
    setError('');
    setSuccessMessage('');
  };

  const backToEmail = () => {
    setAuthStep(AUTH_STEPS.EMAIL);
    setCode('');
    clearError();
  };

  const value: AuthContextType = {
    user,
    authStep,
    authMode,
    email,
    displayName,
    code,
    loading,
    error,
    successMessage,
    setAuthStep,
    setAuthMode,
    setEmail,
    setDisplayName,
    setCode,
    setError,
    setSuccessMessage,
    requestCode,
    verifyCode,
    logout,
    updateProfile,
    clearError,
    backToEmail,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
