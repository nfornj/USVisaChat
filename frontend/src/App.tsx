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
  // Tab, // Commented out - can be restored with AI Assistant
  // Tabs, // Commented out - can be restored with AI Assistant
  Alert,
  Chip,
  CircularProgress,
  Divider,
  Stack,
  ToggleButtonGroup,
  ToggleButton,
  keyframes,
} from "@mui/material";
import {
  Brightness4 as DarkModeIcon,
  Brightness7 as LightModeIcon,
  // Chat as ChatIcon, // Commented out - can be restored with AI Assistant
  // SmartToy as AIIcon, // Commented out - can be restored with AI Assistant
  AccountCircle as AccountIcon,
  Logout as LogoutIcon,
  Close as CloseIcon,
  Email as EmailIcon,
  Lock as LockIcon,
  Groups as GroupsIcon,
  Article as ArticleIcon,
} from "@mui/icons-material";

// Animation keyframes for button effects
const shimmer = keyframes`
  0% {
    background-position: -200px 0;
  }
  100% {
    background-position: calc(200px + 100%) 0;
  }
`;

const glow = keyframes`
  0%, 100% {
    box-shadow: 0 0 5px rgba(0, 0, 0, 0.1);
  }
  50% {
    box-shadow: 0 0 20px rgba(0, 0, 0, 0.2), 0 0 30px rgba(0, 0, 0, 0.1);
  }
`;

const pulse = keyframes`
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.05);
  }
`;

// Import both interfaces
// import AIAssistant from "./AIAssistant"; // Commented out - can be restored later
import CommunityChat from "./CommunityChat";
import TopicsHome from "./pages/TopicsHome";
import AINews from "./components/AINews";
import { authAPI } from "./utils/api";
import { createAppTheme } from "./theme";

// type TabType = "topics" | "community" | "ai"; // Commented out - can be restored with AI Assistant
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

  // Keep Tailwind's dark mode in sync with MUI theme
  useEffect(() => {
    const root = document.documentElement;
    if (darkMode) {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
  }, [darkMode]);

  const [selectedTopic, setSelectedTopic] = useState<{
    id: string;
    name: string;
  } | null>(null);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [onlineCount, setOnlineCount] = useState(0);
  // onlineCount is used via setOnlineCount callback in CommunityChat
  console.debug("Online count:", onlineCount); // Keep variable "used" for TypeScript

  // Tab state (commented out for now - can be restored later)
  // To restore AI Assistant and Community Chat tabs:
  // 1. Uncomment the activeTab state below
  // 2. Uncomment the Tabs component in the header
  // 3. Uncomment the tab-based content routing
  // 4. Remove the current simplified navigation logic
  const [activeTab, setActiveTab] = useState<"topics" | "news">(() => {
    const saved = localStorage.getItem("visa-active-tab");
    return (saved as "topics" | "news") || "topics";
  });

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

  // Show login dialog when needed
  const [showAuthDialog, setShowAuthDialog] = useState(false);

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

  // Handle topic selection - require auth
  const handleTopicSelect = (topicId: string, topicName: string) => {
    if (!userProfile) {
      // Show login dialog
      setShowAuthDialog(true);
    } else {
      setSelectedTopic({ id: topicId, name: topicName });
    }
  };

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
        // Reset to topics view on login
        setSelectedTopic(null);
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

  // Auth dialog (overlay)
  const renderAuthDialog = () => {
    if (!showAuthDialog) return null;

    // Email input step
    if (authStep === "email") {
      return (
        <Dialog open={showAuthDialog} onClose={() => setShowAuthDialog(false)} maxWidth="sm" fullWidth>
          <DialogTitle>
            <Box sx={{ textAlign: "center" }}>
              <Avatar
                sx={{
                  width: 64,
                  height: 64,
                  mx: "auto",
                  mb: 1,
                  background: "linear-gradient(135deg, #6366f1 0%, #a855f7 100%)",
                }}
              >
                <GroupsIcon sx={{ fontSize: 32 }} />
              </Avatar>
              <Typography variant="h5" fontWeight="bold">
                {authMode === "signup" ? "Join H1B Visa Community" : "Welcome Back"}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {authMode === "signup" ? "Create your account to get started" : "Login to your account"}
              </Typography>
            </Box>
          </DialogTitle>
          <DialogContent>
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
              sx={{ mb: 2, mt: 1 }}
            >
              <ToggleButton value="login">Login</ToggleButton>
              <ToggleButton value="signup">Sign Up</ToggleButton>
            </ToggleButtonGroup>

            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

            <form onSubmit={handleRequestCode}>
              <Stack spacing={2}>
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
                    startAdornment: <EmailIcon sx={{ mr: 1, color: "text.secondary" }} />,
                  }}
                />
              </Stack>
            </form>

            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 2, textAlign: "center" }}>
              By continuing, you agree to receive a verification code via email
            </Typography>
          </DialogContent>
          <DialogActions sx={{ px: 3, pb: 3 }}>
            <Button onClick={() => setShowAuthDialog(false)}>Cancel</Button>
            <Button
              onClick={handleRequestCode}
              variant="contained"
              disabled={loading}
              startIcon={loading ? <CircularProgress size={20} /> : <LockIcon />}
            >
              {loading ? "Sending..." : "Continue"}
            </Button>
          </DialogActions>
        </Dialog>
      );
    }

    // Code verification step
    if (authStep === "code") {
      return (
        <Dialog open={showAuthDialog} onClose={() => setShowAuthDialog(false)} maxWidth="sm" fullWidth>
          <DialogTitle>
            <Box sx={{ textAlign: "center" }}>
              <Avatar
                sx={{
                  width: 64,
                  height: 64,
                  mx: "auto",
                  mb: 1,
                  background: "linear-gradient(135deg, #6366f1 0%, #a855f7 100%)",
                }}
              >
                <LockIcon sx={{ fontSize: 32 }} />
              </Avatar>
              <Typography variant="h5" fontWeight="bold">
                Enter Verification Code
              </Typography>
              <Typography variant="body2" color="text.secondary">
                We sent a 6-digit code to
              </Typography>
              <Chip label={email} sx={{ mt: 1 }} />
            </Box>
          </DialogTitle>
          <DialogContent>
            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
            {successMessage && <Alert severity="success" sx={{ mb: 2 }}>{successMessage}</Alert>}

            <form onSubmit={handleVerifyCode}>
              <TextField
                label="6-Digit Code"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
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
                sx={{ mt: 2 }}
              />
            </form>

            <Alert severity="info" sx={{ mt: 2 }}>
              <Typography variant="caption" fontWeight="bold">📧 DEV MODE:</Typography>
              <Typography variant="caption" display="block">
                Check the server logs for your verification code
              </Typography>
              <Typography variant="caption" display="block" sx={{ mt: 0.5, fontFamily: "monospace" }}>
                docker compose logs visa-web --tail 20
              </Typography>
            </Alert>
          </DialogContent>
          <DialogActions sx={{ px: 3, pb: 3 }}>
            <Button onClick={handleBackToEmail}>← Back to email</Button>
            <Button
              onClick={handleVerifyCode}
              variant="contained"
              disabled={loading || code.length !== 6}
              startIcon={loading ? <CircularProgress size={20} /> : null}
            >
              {loading ? "Verifying..." : "Verify & Login"}
            </Button>
          </DialogActions>
        </Dialog>
      );
    }

    return null;
  };

  // Close auth dialog on successful login
  useEffect(() => {
    if (authStep === "authenticated" && showAuthDialog) {
      setShowAuthDialog(false);
    }
  }, [authStep, showAuthDialog]);

  // Main application (always shown, public or authenticated)
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
              H1B Visa Community
            </Typography>

            <Box sx={{ flexGrow: 1 }} />

            {/* Topics Button */}
            <Chip
              icon={<GroupsIcon />}
              label="Topics"
              color="primary"
              sx={{
                fontWeight: 500,
                mr: 2,
                cursor: "pointer",
                "&:hover": {
                  bgcolor: "primary.dark",
                  animation: `${pulse} 0.5s ease-in-out`,
                  transform: "scale(1.02)",
                },
                "& .MuiChip-icon": {
                  "&:hover": {
                    animation: `${pulse} 0.3s ease-in-out`,
                  },
                },
              }}
              onClick={() => setSelectedTopic(null)}
            />

            {/* AI News Button */}
            <Chip
              icon={<ArticleIcon />}
              label="AI News"
              color="secondary"
              sx={{
                fontWeight: 500,
                mr: 2,
                cursor: "pointer",
                position: "relative",
                overflow: "hidden",
                background:
                  "linear-gradient(90deg, #9c27b0 0%, #e91e63 50%, #9c27b0 100%)",
                backgroundSize: "200% 100%",
                animation: `${shimmer} 3s ease-in-out infinite`,
                "&:hover": {
                  bgcolor: "secondary.dark",
                  animation: `${pulse} 1s ease-in-out infinite, ${glow} 1s ease-in-out infinite`,
                  transform: "scale(1.05)",
                },
                "& .MuiChip-label": {
                  background:
                    "linear-gradient(90deg, #fff 0%, #f0f0f0 50%, #fff 100%)",
                  backgroundSize: "200% 100%",
                  backgroundClip: "text",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  animation: `${shimmer} 2.5s ease-in-out infinite`,
                },
                "& .MuiChip-icon": {
                  animation: `${pulse} 2s ease-in-out infinite`,
                  "&:hover": {
                    animation: `${pulse} 0.5s ease-in-out infinite`,
                  },
                },
                "&::before": {
                  content: '""',
                  position: "absolute",
                  top: 0,
                  left: "-100%",
                  width: "100%",
                  height: "100%",
                  background:
                    "linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent)",
                  animation: `${shimmer} 2s ease-in-out infinite`,
                },
              }}
              onClick={() => setActiveTab("news")}
            />

            {/* COMMENTED OUT: Tabs for Community Chat and AI Assistant - can be restored later */}
            {/* 
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
            */}

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
        <Box
          sx={{
            flexGrow: 1,
            overflow: "auto",
            WebkitOverflowScrolling: "touch",
            minHeight: 0,
          }}
        >
          {activeTab === "news" ? (
            <AINews onBackToTopics={() => setActiveTab("topics")} />
          ) : !selectedTopic ? (
            <TopicsHome onTopicSelect={handleTopicSelect} />
          ) : userProfile ? (
            <CommunityChat
              userEmail={userProfile.email}
              displayName={userProfile.displayName}
              onOnlineCountChange={setOnlineCount}
              roomId={selectedTopic.id}
              roomName={selectedTopic.name}
              onBackToTopics={() => setSelectedTopic(null)}
            />
          ) : null}
        </Box>

        {/* Auth Dialog */}
        {renderAuthDialog()}

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
