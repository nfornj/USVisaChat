/**
 * LoginForm Component
 * Handles email and display name input for login/signup
 */

import {
  Stack,
  TextField,
  Button,
  Alert,
  CircularProgress,
  ToggleButtonGroup,
  ToggleButton,
  Typography,
} from '@mui/material';
import { Email as EmailIcon, Lock as LockIcon } from '@mui/icons-material';
import { useAuth } from '../../../contexts/AuthContext';
import { AUTH_MODES } from '../../../config/constants';

export function LoginForm() {
  const {
    authMode,
    setAuthMode,
    email,
    setEmail,
    displayName,
    setDisplayName,
    loading,
    error,
    requestCode,
    clearError,
  } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await requestCode();
  };

  return (
    <>
      <ToggleButtonGroup
        value={authMode}
        exclusive
        onChange={(_, value) => {
          if (value !== null) {
            setAuthMode(value);
            clearError();
            setDisplayName('');
          }
        }}
        fullWidth
        sx={{ mb: 2, mt: 1 }}
      >
        <ToggleButton value={AUTH_MODES.LOGIN}>Login</ToggleButton>
        <ToggleButton value={AUTH_MODES.SIGNUP}>Sign Up</ToggleButton>
      </ToggleButtonGroup>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <form onSubmit={handleSubmit}>
        <Stack spacing={2}>
          {authMode === AUTH_MODES.SIGNUP && (
            <TextField
              label="Your Name"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="e.g., Alice Johnson"
              required={authMode === AUTH_MODES.SIGNUP}
              fullWidth
              autoFocus={authMode === AUTH_MODES.SIGNUP}
            />
          )}
          <TextField
            type="email"
            label="Email Address"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            required
            fullWidth
            autoFocus={authMode === AUTH_MODES.LOGIN}
            InputProps={{
              startAdornment: <EmailIcon sx={{ mr: 1, color: 'text.secondary' }} />,
            }}
          />
        </Stack>

        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ display: 'block', mt: 2, textAlign: 'center' }}
        >
          By continuing, you agree to receive a verification code via email
        </Typography>

        <Button
          type="submit"
          variant="contained"
          fullWidth
          disabled={loading}
          startIcon={loading ? <CircularProgress size={20} /> : <LockIcon />}
          sx={{ mt: 3 }}
        >
          {loading ? 'Sending...' : 'Continue'}
        </Button>
      </form>
    </>
  );
}
