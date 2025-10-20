import { useState, useEffect, useMemo } from "react";
import {
  ThemeProvider,
  CssBaseline,
  Box,
  AppBar,
  Toolbar,
  Typography,
  Button,
  IconButton,
  Avatar,
  Menu,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Tab,
  Tabs,
  Card,
  CardContent,
  Alert,
  Chip,
  CircularProgress,
  Divider,
  Stack,
  ToggleButtonGroup,
  ToggleButton,
} from "@mui/material";
import {
  Brightness4 as DarkModeIcon,
  Brightness7 as LightModeIcon,
  Chat as ChatIcon,
  SmartToy as AIIcon,
  AccountCircle as AccountIcon,
  Logout as LogoutIcon,
  Close as CloseIcon,
  Email as EmailIcon,
  Lock as LockIcon,
  Groups as GroupsIcon,
} from "@mui/icons-material";

// Import both interfaces
import AIAssistant from "./AIAssistant";
import CommunityChat from "./CommunityChat";
import TopicsHome from "./pages/TopicsHome";
import { authAPI } from "./utils/api";
import { createAppTheme } from "./theme";

type TabType = "topics" | "community" | "ai";
type AuthStep = "email" | "code" | "authenticated";
type AuthMode = "signup" | "login";

interface UserProfile {
  id: number;
  email: string;
  displayName: string;
  isVerified: boolean;
}

function App() {
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem("visa-dark-mode");
    return saved ? JSON.parse(saved) : true;
  });
  const theme = useMemo(
    () => createAppTheme(darkMode ? "dark" : "light"),
    [darkMode]
  );

  const [activeTab, setActiveTab] = useState<TabType>(() => {
    const saved = localStorage.getItem("visa-active-tab");
    return (saved as TabType) || "topics";
  });
  const [selectedTopic, setSelectedTopic] = useState<{
    id: string;
    name: string;
  } | null>(null);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [onlineCount, setOnlineCount] = useState(0);

  // Authentication state
  const [authStep, setAuthStep] = useState<AuthStep>("email");
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  // Profile modal state
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [newDisplayName, setNewDisplayName] = useState("");
  const [profileError, setProfileError] = useState("");
  const [profileSuccess, setProfileSuccess] = useState("");
  const [profileLoading, setProfileLoading] = useState(false);

  // User menu
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  // Toggle dark mode
  const toggleDarkMode = () => {
    const newMode = !darkMode;
    setDarkMode(newMode);
    localStorage.setItem("visa-dark-mode", JSON.stringify(newMode));
  };

  // Check for saved session
  useEffect(() => {
    const checkSession = async () => {
      const sessionToken = localStorage.getItem("visa-session-token");
      if (sessionToken) {
        try {
          const response = await authAPI.verifySession(sessionToken);
          if (response.success && response.user) {
            setUserProfile(response.user);
            setAuthStep("authenticated");
          } else {
            localStorage.removeItem("visa-session-token");
          }
        } catch (err) {
          console.error("Session verification failed:", err);
          localStorage.removeItem("visa-session-token");
        }
      }
    };

    checkSession();
  }, []);

  const handleRequestCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccessMessage("");

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email || !emailRegex.test(email.trim())) {
      setError("Please enter a valid email address");
      return;
    }

    if (authMode === "signup") {
      if (!displayName || displayName.trim().length < 2) {
        setError("Please enter a display name (at least 2 characters)");
        return;
      }

      if (displayName.trim().length > 30) {
        setError("Display name must be 30 characters or less");
        return;
      }
    }

    setLoading(true);

    try {
      const nameToUse =
        authMode === "signup" ? displayName.trim() : email.trim().split("@")[0];

      const response = await authAPI.requestCode(
        email.trim().toLowerCase(),
        nameToUse
      );

      if (response.success) {
        setSuccessMessage(response.message);
        setAuthStep("code");
      } else {
        setError("Failed to send verification code. Please try again.");
      }
    } catch (err) {
      setError("Failed to send verification code. Please try again.");
      console.error("Request code error:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccessMessage("");

    if (!code || code.trim().length !== 6) {
      setError("Please enter a valid 6-digit code");
      return;
    }

    setLoading(true);

    try {
      const response = await authAPI.verifyCode(
        email.trim().toLowerCase(),
        code.trim()
      );

      if (response.success && response.session_token && response.user) {
        localStorage.setItem("visa-session-token", response.session_token);
        setUserProfile(response.user);
        setAuthStep("authenticated");
        // Reset to topics tab on login
        setActiveTab("topics");
        localStorage.setItem("visa-active-tab", "topics");
        setSuccessMessage("Successfully logged in!");
      } else {
        setError(response.message || "Invalid verification code");
      }
    } catch (err) {
      setError("Failed to verify code. Please try again.");
      console.error("Verify code error:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    const sessionToken = localStorage.getItem("visa-session-token");
    if (sessionToken) {
      try {
        await authAPI.logout(sessionToken);
      } catch (err) {
        console.error("Logout error:", err);
      }
    }

    localStorage.removeItem("visa-session-token");
    setUserProfile(null);
    setAuthStep("email");
    setEmail("");
    setDisplayName("");
    setCode("");
    setAnchorEl(null);
  };

  const handleBackToEmail = () => {
    setAuthStep("email");
    setCode("");
    setError("");
    setSuccessMessage("");
  };

  const handleOpenProfile = () => {
    setNewDisplayName(userProfile?.displayName || "");
    setProfileError("");
    setProfileSuccess("");
    setShowProfileModal(true);
    setAnchorEl(null);
  };

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setProfileError("");
    setProfileSuccess("");

    if (!newDisplayName || newDisplayName.trim().length < 2) {
      setProfileError("Display name must be at least 2 characters");
      return;
    }

    if (newDisplayName.trim().length > 30) {
      setProfileError("Display name must be 30 characters or less");
      return;
    }

    setProfileLoading(true);

    try {
      const sessionToken = localStorage.getItem("visa-session-token");
      if (!sessionToken) {
        setProfileError("Session expired. Please login again.");
        return;
      }

      const response = await authAPI.updateProfile(
        sessionToken,
        newDisplayName.trim()
      );

      if (response.success && response.user) {
        setUserProfile(response.user);
        setProfileSuccess("Profile updated successfully!");
        setTimeout(() => {
          setShowProfileModal(false);
        }, 1500);
      } else {
        setProfileError(response.message || "Failed to update profile");
      }
    } catch (err) {
      setProfileError("Failed to update profile. Please try again.");
      console.error("Profile update error:", err);
    } finally {
      setProfileLoading(false);
    }
  };

  // Email input screen (Step 1)
  if (authStep === "email") {
    return (
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Box
          sx={{
            minHeight: "100vh",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: darkMode
              ? "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)"
              : "linear-gradient(135deg, #EEF2FF 0%, #F3E8FF 100%)",
            p: 2,
          }}
        >
          <Card sx={{ maxWidth: 480, width: "100%", p: 2 }}>
            <CardContent>
              <Box sx={{ textAlign: "center", mb: 4 }}>
                <Avatar
                  sx={{
                    width: 80,
                    height: 80,
                    mx: "auto",
                    mb: 2,
                    background:
                      "linear-gradient(135deg, #6366f1 0%, #a855f7 100%)",
                  }}
                >
                  <GroupsIcon sx={{ fontSize: 40 }} />
                </Avatar>
                <Typography variant="h4" fontWeight="bold" gutterBottom>
                  {authMode === "signup"
                    ? "Join Visa Community"
                    : "Welcome Back"}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {authMode === "signup"
                    ? "Create your account to get started"
                    : "Login to your account"}
                </Typography>
              </Box>

              {/* Toggle between Sign Up and Login */}
              <ToggleButtonGroup
                value={authMode}
                exclusive
                onChange={(_, value) => {
                  if (value !== null) {
                    setAuthMode(value);
                    setError("");
                    setSuccessMessage("");
                    setDisplayName("");
                  }
                }}
                fullWidth
                sx={{ mb: 3 }}
              >
                <ToggleButton value="login">Login</ToggleButton>
                <ToggleButton value="signup">Sign Up</ToggleButton>
              </ToggleButtonGroup>

              {error && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {error}
                </Alert>
              )}

              <form onSubmit={handleRequestCode}>
                <Stack spacing={2.5}>
                  {authMode === "signup" && (
                    <TextField
                      label="Your Name"
                      value={displayName}
                      onChange={(e) => setDisplayName(e.target.value)}
                      placeholder="e.g., Alice Johnson"
                      required={authMode === "signup"}
                      fullWidth
                      autoFocus={authMode === "signup"}
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
                    autoFocus={authMode === "login"}
                    InputProps={{
                      startAdornment: (
                        <EmailIcon sx={{ mr: 1, color: "text.secondary" }} />
                      ),
                    }}
                  />

                  <Button
                    type="submit"
                    variant="contained"
                    size="large"
                    fullWidth
                    disabled={loading}
                    startIcon={
                      loading ? <CircularProgress size={20} /> : <LockIcon />
                    }
                  >
                    {loading ? "Sending..." : "Continue"}
                  </Button>
                </Stack>
              </form>

              <Box sx={{ mt: 3, textAlign: "center" }}>
                <Typography variant="caption" color="text.secondary">
                  By continuing, you agree to receive a verification code via
                  email
                </Typography>
              </Box>
            </CardContent>
          </Card>

          {/* Dark mode toggle */}
          <IconButton
            onClick={toggleDarkMode}
            sx={{
              position: "absolute",
              top: 16,
              right: 16,
            }}
          >
            {darkMode ? <LightModeIcon /> : <DarkModeIcon />}
          </IconButton>
        </Box>
      </ThemeProvider>
    );
  }

  // Code verification screen (Step 2)
  if (authStep === "code") {
    return (
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Box
          sx={{
            minHeight: "100vh",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: darkMode
              ? "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)"
              : "linear-gradient(135deg, #EEF2FF 0%, #F3E8FF 100%)",
            p: 2,
          }}
        >
          <Card sx={{ maxWidth: 480, width: "100%", p: 2 }}>
            <CardContent>
              <Box sx={{ textAlign: "center", mb: 4 }}>
                <Avatar
                  sx={{
                    width: 80,
                    height: 80,
                    mx: "auto",
                    mb: 2,
                    background:
                      "linear-gradient(135deg, #6366f1 0%, #a855f7 100%)",
                  }}
                >
                  <LockIcon sx={{ fontSize: 40 }} />
                </Avatar>
                <Typography variant="h4" fontWeight="bold" gutterBottom>
                  Enter Verification Code
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  We sent a 6-digit code to
                </Typography>
                <Chip label={email} sx={{ mt: 1 }} />
              </Box>

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

              <form onSubmit={handleVerifyCode}>
                <Stack spacing={2.5}>
                  <TextField
                    label="6-Digit Code"
                    value={code}
                    onChange={(e) =>
                      setCode(e.target.value.replace(/\D/g, "").slice(0, 6))
                    }
                    placeholder="000000"
                    required
                    fullWidth
                    autoFocus
                    inputProps={{
                      maxLength: 6,
                      style: {
                        textAlign: "center",
                        fontSize: "1.5rem",
                        letterSpacing: "0.5rem",
                      },
                    }}
                  />

                  <Button
                    type="submit"
                    variant="contained"
                    size="large"
                    fullWidth
                    disabled={loading || code.length !== 6}
                    startIcon={loading ? <CircularProgress size={20} /> : null}
                  >
                    {loading ? "Verifying..." : "Verify & Login"}
                  </Button>

                  <Button onClick={handleBackToEmail} variant="text" fullWidth>
                    ← Back to email
                  </Button>
                </Stack>
              </form>

              <Alert severity="info" sx={{ mt: 3 }}>
                <Typography variant="caption" fontWeight="bold">
                  📧 DEV MODE:
                </Typography>
                <Typography variant="caption" display="block">
                  Check the server logs for your verification code
                </Typography>
                <Typography
                  variant="caption"
                  display="block"
                  sx={{ mt: 0.5, fontFamily: "monospace" }}
                >
                  docker compose logs visa-web --tail 20
                </Typography>
              </Alert>
            </CardContent>
          </Card>

          <IconButton
            onClick={toggleDarkMode}
            sx={{
              position: "absolute",
              top: 16,
              right: 16,
            }}
          >
            {darkMode ? <LightModeIcon /> : <DarkModeIcon />}
          </IconButton>
        </Box>
      </ThemeProvider>
    );
  }

  // Main application (authenticated)
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: "flex", flexDirection: "column", height: "100vh" }}>
        {/* Header */}
        <AppBar
          position="static"
          elevation={0}
          sx={{ borderBottom: 1, borderColor: "divider" }}
        >
          <Toolbar>
            {/* Logo */}
            <Avatar
              sx={{
                width: 40,
                height: 40,
                mr: 2,
                background: "linear-gradient(135deg, #6366f1 0%, #a855f7 100%)",
              }}
            >
              <GroupsIcon />
            </Avatar>
            <Typography variant="h6" component="div" fontWeight="bold">
              Visa Community
            </Typography>

            <Box sx={{ flexGrow: 1 }} />

            {/* Tabs */}
            <Tabs
              value={activeTab}
              onChange={(_, value) => {
                setActiveTab(value);
                localStorage.setItem("visa-active-tab", value);
              }}
              sx={{ mr: 2 }}
              TabIndicatorProps={{
                style: { display: "none" },
              }}
            >
              <Tab
                label={
                  <Chip
                    icon={<GroupsIcon />}
                    label="Topics"
                    color={activeTab === "topics" ? "primary" : "default"}
                    sx={{ fontWeight: 500 }}
                  />
                }
                value="topics"
                sx={{ minHeight: 48, textTransform: "none" }}
              />
              <Tab
                label={
                  <Chip
                    icon={<ChatIcon />}
                    label={`Community Chat${
                      onlineCount > 0 ? ` (${onlineCount})` : ""
                    }${selectedTopic ? `: ${selectedTopic.name}` : ""}`}
                    color={activeTab === "community" ? "primary" : "default"}
                    sx={{ fontWeight: 500 }}
                  />
                }
                value="community"
                sx={{ minHeight: 48, textTransform: "none" }}
              />
              <Tab
                label={
                  <Chip
                    icon={<AIIcon />}
                    label="AI Assistant"
                    color={activeTab === "ai" ? "primary" : "default"}
                    sx={{ fontWeight: 500 }}
                  />
                }
                value="ai"
                sx={{ minHeight: 48, textTransform: "none" }}
              />
            </Tabs>

            {/* User menu */}
            {userProfile && (
              <>
                <IconButton
                  onClick={(e) => setAnchorEl(e.currentTarget)}
                  size="large"
                >
                  <Avatar sx={{ bgcolor: "primary.main" }}>
                    {userProfile.displayName.charAt(0).toUpperCase()}
                  </Avatar>
                </IconButton>

                <Menu
                  anchorEl={anchorEl}
                  open={Boolean(anchorEl)}
                  onClose={() => setAnchorEl(null)}
                  PaperProps={{
                    sx: { minWidth: 240, mt: 1 },
                  }}
                >
                  <Box sx={{ px: 2, py: 1.5 }}>
                    <Typography variant="subtitle2" fontWeight="bold">
                      {userProfile.displayName}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {userProfile.email}
                    </Typography>
                  </Box>
                  <Divider />
                  <MenuItem onClick={handleOpenProfile}>
                    <AccountIcon sx={{ mr: 1.5 }} fontSize="small" />
                    Edit Profile
                  </MenuItem>
                  <MenuItem onClick={handleLogout} sx={{ color: "error.main" }}>
                    <LogoutIcon sx={{ mr: 1.5 }} fontSize="small" />
                    Logout
                  </MenuItem>
                </Menu>
              </>
            )}

            <IconButton onClick={toggleDarkMode} sx={{ ml: 1 }}>
              {darkMode ? <LightModeIcon /> : <DarkModeIcon />}
            </IconButton>
          </Toolbar>
        </AppBar>

        {/* Content */}
        <Box sx={{ flexGrow: 1, overflow: "hidden" }}>
          {userProfile && (
            <>
              {activeTab === "topics" && (
                <TopicsHome
                  onTopicSelect={(topicId, topicName) => {
                    setSelectedTopic({ id: topicId, name: topicName });
                    setActiveTab("community");
                  }}
                />
              )}
              {activeTab === "community" && (
                <CommunityChat
                  userEmail={userProfile.email}
                  displayName={userProfile.displayName}
                  onOnlineCountChange={setOnlineCount}
                />
              )}
              {activeTab === "ai" && <AIAssistant />}
            </>
          )}
        </Box>

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
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
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
            {profileError && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {profileError}
              </Alert>
            )}

            {profileSuccess && (
              <Alert severity="success" sx={{ mb: 2 }}>
                {profileSuccess}
              </Alert>
            )}

            <form onSubmit={handleUpdateProfile}>
              <Stack spacing={3} sx={{ mt: 1 }}>
                <TextField
                  label="Email"
                  value={userProfile?.email || ""}
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
                  inputProps={{ maxLength: 30 }}
                  helperText={`${newDisplayName.length}/30 characters`}
                />
              </Stack>
            </form>
          </DialogContent>
          <DialogActions sx={{ px: 3, pb: 3 }}>
            <Button
              onClick={() => setShowProfileModal(false)}
              disabled={profileLoading}
            >
              Cancel
            </Button>
            <Button
              onClick={handleUpdateProfile}
              variant="contained"
              disabled={profileLoading}
              startIcon={profileLoading ? <CircularProgress size={20} /> : null}
            >
              {profileLoading ? "Saving..." : "Save Changes"}
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    </ThemeProvider>
  );
}

export default App;
