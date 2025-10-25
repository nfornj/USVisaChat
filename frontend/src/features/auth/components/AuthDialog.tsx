/**
 * AuthDialog Component
 * Modal dialog for authentication flow
 */

import { useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  Box,
  Avatar,
  Typography,
} from '@mui/material';
import { Groups as GroupsIcon, Lock as LockIcon } from '@mui/icons-material';
import { useAuth } from '../../../contexts/AuthContext';
import { LoginForm } from './LoginForm';
import { VerificationForm } from './VerificationForm';
import { AUTH_STEPS, AUTH_MODES, UI_CONFIG } from '../../../config/constants';

interface AuthDialogProps {
  open: boolean;
  onClose: () => void;
}

export function AuthDialog({ open, onClose }: AuthDialogProps) {
  const { authStep, authMode, setAuthStep } = useAuth();

  // Close dialog when authenticated
  useEffect(() => {
    if (authStep === AUTH_STEPS.AUTHENTICATED) {
      onClose();
      // Reset to email step for next time
      setTimeout(() => setAuthStep(AUTH_STEPS.EMAIL), 300);
    }
  }, [authStep, onClose, setAuthStep]);

  const isEmailStep = authStep === AUTH_STEPS.EMAIL;
  const isCodeStep = authStep === AUTH_STEPS.CODE;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Box sx={{ textAlign: 'center' }}>
          <Avatar
            sx={{
              width: UI_CONFIG.AVATAR_SIZE.LARGE,
              height: UI_CONFIG.AVATAR_SIZE.LARGE,
              mx: 'auto',
              mb: 1,
              background: 'linear-gradient(135deg, #6366f1 0%, #a855f7 100%)',
            }}
          >
            {isEmailStep ? (
              <GroupsIcon sx={{ fontSize: 32 }} />
            ) : (
              <LockIcon sx={{ fontSize: 32 }} />
            )}
          </Avatar>

          {isEmailStep && (
            <>
              <Typography variant="h5" fontWeight="bold">
                {authMode === AUTH_MODES.SIGNUP ? 'Join H1B Visa Community' : 'Welcome Back'}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {authMode === AUTH_MODES.SIGNUP
                  ? 'Create your account to get started'
                  : 'Login to your account'}
              </Typography>
            </>
          )}

          {isCodeStep && (
            <>
              <Typography variant="h5" fontWeight="bold">
                Enter Verification Code
              </Typography>
            </>
          )}
        </Box>
      </DialogTitle>

      <DialogContent>
        {isEmailStep && <LoginForm />}
        {isCodeStep && <VerificationForm />}
      </DialogContent>
    </Dialog>
  );
}
