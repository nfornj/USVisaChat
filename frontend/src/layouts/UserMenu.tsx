/**
 * UserMenu Component
 * User dropdown menu with profile and logout options
 */

import { useState } from 'react';
import {
  IconButton,
  Avatar,
  Menu,
  MenuItem,
  Box,
  Typography,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Stack,
  Alert,
  CircularProgress,
} from '@mui/material';
import {
  AccountCircle as AccountIcon,
  Logout as LogoutIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import { VALIDATION } from '../config/constants';

export function UserMenu() {
  const { user, logout, updateProfile, loading, error, successMessage, setError, setSuccessMessage } = useAuth();
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [newDisplayName, setNewDisplayName] = useState('');

  const handleOpenMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleCloseMenu = () => {
    setAnchorEl(null);
  };

  const handleOpenProfile = () => {
    setNewDisplayName(user?.displayName || '');
    setError('');
    setSuccessMessage('');
    setShowProfileModal(true);
    handleCloseMenu();
  };

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    const success = await updateProfile(newDisplayName);
    if (success) {
      setTimeout(() => {
        setShowProfileModal(false);
      }, 1500);
    }
  };

  const handleLogout = async () => {
    handleCloseMenu();
    await logout();
  };

  if (!user) return null;

  return (
    <>
      <IconButton onClick={handleOpenMenu} size="large">
        <Avatar sx={{ bgcolor: 'primary.main' }}>
          {user.displayName.charAt(0).toUpperCase()}
        </Avatar>
      </IconButton>

      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleCloseMenu}
        PaperProps={{
          sx: { minWidth: 240, mt: 1 },
        }}
      >
        <Box sx={{ px: 2, py: 1.5 }}>
          <Typography variant="subtitle2" fontWeight="bold">
            {user.displayName}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {user.email}
          </Typography>
        </Box>
        <Divider />
        <MenuItem onClick={handleOpenProfile}>
          <AccountIcon sx={{ mr: 1.5 }} fontSize="small" />
          Edit Profile
        </MenuItem>
        <MenuItem onClick={handleLogout} sx={{ color: 'error.main' }}>
          <LogoutIcon sx={{ mr: 1.5 }} fontSize="small" />
          Logout
        </MenuItem>
      </Menu>

      {/* Profile Modal */}
      <Dialog
        open={showProfileModal}
        onClose={() => setShowProfileModal(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <Typography variant="h5" fontWeight="bold">
              Edit Profile
            </Typography>
            <IconButton onClick={() => setShowProfileModal(false)}>
              <CloseIcon />
            </IconButton>
          </Box>
        </DialogTitle>
        <DialogContent>
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

          <form onSubmit={handleUpdateProfile}>
            <Stack spacing={3} sx={{ mt: 1 }}>
              <TextField
                label="Email"
                value={user.email}
                disabled
                fullWidth
                helperText="Email cannot be changed"
              />

              <TextField
                label="Display Name"
                value={newDisplayName}
                onChange={(e) => setNewDisplayName(e.target.value)}
                placeholder="e.g., Alice Johnson"
                required
                fullWidth
                inputProps={{ maxLength: VALIDATION.MAX_DISPLAY_NAME_LENGTH }}
                helperText={`${newDisplayName.length}/${VALIDATION.MAX_DISPLAY_NAME_LENGTH} characters`}
              />
            </Stack>
          </form>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 3 }}>
          <Button onClick={() => setShowProfileModal(false)} disabled={loading}>
            Cancel
          </Button>
          <Button
            onClick={handleUpdateProfile}
            variant="contained"
            disabled={loading}
            startIcon={loading ? <CircularProgress size={20} /> : null}
          >
            {loading ? 'Saving...' : 'Save Changes'}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
