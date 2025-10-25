/**
 * VerificationForm Component
 * Handles 6-digit code verification
 */

import {
  TextField,
  Button,
  Alert,
  CircularProgress,
  Typography,
  Chip,
} from '@mui/material';
import { useAuth } from '../../../contexts/AuthContext';
import { VALIDATION, UI_CONFIG } from '../../../config/constants';

export function VerificationForm() {
  const {
    email,
    code,
    setCode,
    loading,
    error,
    successMessage,
    verifyCode,
    backToEmail,
  } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await verifyCode();
  };

  return (
    <>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      {successMessage && (
        <Alert severity="success" sx={{ mb: 2 }}>
          {successMessage}
        </Alert>
      )}

      <Typography variant="body2" color="text.secondary" align="center" sx={{ mb: 1 }}>
        We sent a {VALIDATION.VERIFICATION_CODE_LENGTH}-digit code to
      </Typography>
      <Chip label={email} sx={{ mb: 2, mx: 'auto', display: 'block', width: 'fit-content' }} />

      <form onSubmit={handleSubmit}>
        <TextField
          label={`${VALIDATION.VERIFICATION_CODE_LENGTH}-Digit Code`}
          value={code}
          onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, VALIDATION.VERIFICATION_CODE_LENGTH))}
          placeholder="000000"
          required
          fullWidth
          autoFocus
          inputProps={{
            maxLength: VALIDATION.VERIFICATION_CODE_LENGTH,
            style: {
              textAlign: 'center',
              fontSize: UI_CONFIG.CODE_INPUT_FONT_SIZE,
              letterSpacing: UI_CONFIG.CODE_INPUT_LETTER_SPACING,
            },
          }}
          sx={{ mb: 2 }}
        />

        <Alert severity="info" sx={{ mb: 3 }}>
          <Typography variant="caption" fontWeight="bold">
            📧 DEV MODE:
          </Typography>
          <Typography variant="caption" display="block">
            Check the server logs for your verification code
          </Typography>
          <Typography
            variant="caption"
            display="block"
            sx={{ mt: 0.5, fontFamily: 'monospace' }}
          >
            docker compose logs visa-web --tail 20
          </Typography>
        </Alert>

        <Button
          onClick={backToEmail}
          fullWidth
          sx={{ mb: 1 }}
        >
          ← Back to email
        </Button>

        <Button
          type="submit"
          variant="contained"
          fullWidth
          disabled={loading || code.length !== VALIDATION.VERIFICATION_CODE_LENGTH}
          startIcon={loading ? <CircularProgress size={20} /> : null}
        >
          {loading ? 'Verifying...' : 'Verify & Login'}
        </Button>
      </form>
    </>
  );
}
