import { useState, useEffect, useRef } from "react";
import {
  Box,
  Paper,
  TextField,
  IconButton,
  Typography,
  Avatar,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  Alert,
  CircularProgress,
  Divider,
} from "@mui/material";
import {
  Send as SendIcon,
  Info as InfoIcon,
  Reply as ReplyIcon,
  Close as CloseIcon,
  Image as ImageIcon,
  AttachFile as AttachFileIcon,
} from "@mui/icons-material";

interface ReplyToMessage {
  id: string;
  userEmail: string;
  displayName: string;
  message: string;
}

interface Message {
  id?: number;
  userEmail: string;
  displayName: string;
  message: string;
  timestamp: string;
  type?: string;
  messageType?: string;
  imageUrl?: string;
  replyTo?: ReplyToMessage;
}

interface OnlineUser {
  email: string;
  displayName: string;
}

interface CommunityChatProps {
  userEmail: string;
  displayName: string;
  onOnlineCountChange: (count: number) => void;
}

export default function CommunityChat({
  userEmail,
  displayName,
  onOnlineCountChange,
}: CommunityChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [onlineUsers, setOnlineUsers] = useState<OnlineUser[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(true);
  const [replyingTo, setReplyingTo] = useState<Message | null>(null);

  // Image upload state
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  // Resizable sidebar state
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    const saved = localStorage.getItem("visa-chat-sidebar-width");
    return saved ? parseInt(saved, 10) : 280;
  });
  const [isResizing, setIsResizing] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const previousDisplayNameRef = useRef<string>(displayName);
  const fileInputRef = useRef<HTMLInputElement>(null);

  console.log("Connected as:", displayName, userEmail);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // WebSocket connection
  useEffect(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${
      window.location.host
    }/ws/chat/${encodeURIComponent(userEmail)}/${encodeURIComponent(
      displayName
    )}`;

    console.log("Connecting to WebSocket:", wsUrl, "as", displayName);
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log("WebSocket connected");
      setIsConnected(true);
      setIsConnecting(false);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log("WebSocket message:", data);

      switch (data.type) {
        case "history":
          setMessages(data.messages || []);
          break;

        case "message":
          setMessages((prev) => [
            ...prev,
            {
              id: data.id,
              userEmail: data.userEmail,
              displayName: data.displayName,
              message: data.message,
              timestamp: data.timestamp,
              replyTo: data.replyTo,
            },
          ]);
          break;

        case "system":
          setMessages((prev) => [
            ...prev,
            {
              userEmail: "system",
              displayName: "System",
              message: data.message,
              timestamp: data.timestamp,
              type: "system",
            },
          ]);
          break;

        case "users":
          setOnlineUsers(data.users || []);
          onOnlineCountChange(data.count || 0);
          break;
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      setIsConnecting(false);
    };

    ws.onclose = () => {
      console.log("WebSocket disconnected");
      setIsConnected(false);
      setIsConnecting(false);
    };

    wsRef.current = ws;

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [userEmail, onOnlineCountChange]);

  // Handle display name changes without reconnecting
  useEffect(() => {
    if (previousDisplayNameRef.current === displayName) {
      return;
    }

    if (wsRef.current && isConnected) {
      console.log("Sending profile update:", displayName);
      wsRef.current.send(
        JSON.stringify({
          type: "profile_update",
          displayName: displayName,
        })
      );
    }

    previousDisplayNameRef.current = displayName;
  }, [displayName, isConnected]);

  // Handle image file selection
  const handleImageSelect = (file: File) => {
    if (!file.type.startsWith("image/")) {
      alert("Please select an image file");
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      // 10MB limit
      alert("Image too large (max 10MB)");
      return;
    }

    setSelectedImage(file);

    // Create preview
    const reader = new FileReader();
    reader.onload = (e) => {
      setImagePreview(e.target?.result as string);
    };
    reader.readAsDataURL(file);
  };

  // Handle paste event for screenshots
  useEffect(() => {
    const handlePaste = (e: ClipboardEvent) => {
      const items = e.clipboardData?.items;
      if (!items) return;

      for (let i = 0; i < items.length; i++) {
        if (items[i].type.indexOf("image") !== -1) {
          const file = items[i].getAsFile();
          if (file) {
            e.preventDefault();
            handleImageSelect(file);
          }
        }
      }
    };

    document.addEventListener("paste", handlePaste);
    return () => document.removeEventListener("paste", handlePaste);
  }, []);

  // Upload image to server
  const uploadImage = async (file: File): Promise<string | null> => {
    try {
      setIsUploading(true);
      const sessionToken = localStorage.getItem("visa-session-token");

      if (!sessionToken) {
        alert("Session expired. Please log in again.");
        return null;
      }

      const formData = new FormData();
      formData.append("file", file);
      formData.append("session_token", sessionToken);

      const response = await fetch("/chat/upload-image", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Upload failed");
      }

      const data = await response.json();
      return data.url;
    } catch (error) {
      console.error("Image upload error:", error);
      alert("Failed to upload image");
      return null;
    } finally {
      setIsUploading(false);
    }
  };

  // Send image message
  const sendImageMessage = async () => {
    if (!selectedImage || !wsRef.current || !isConnected) return;

    const imageUrl = await uploadImage(selectedImage);
    if (!imageUrl) return;

    const messageData: any = {
      type: "image",
      message: input.trim() || "Sent an image",
      imageUrl: imageUrl,
    };

    // Include reply information if replying
    if (replyingTo) {
      messageData.replyTo = replyingTo.id;
    }

    wsRef.current.send(JSON.stringify(messageData));

    // Clear state
    setInput("");
    setSelectedImage(null);
    setImagePreview(null);
    setReplyingTo(null);
  };

  const sendMessage = () => {
    // If image is selected, send image message
    if (selectedImage) {
      sendImageMessage();
      return;
    }

    if (!input.trim() || !wsRef.current || !isConnected) return;

    const messageData: any = {
      type: "text",
      message: input.trim(),
    };

    // Include reply information if replying
    if (replyingTo) {
      messageData.replyTo = replyingTo.id;
    }

    wsRef.current.send(JSON.stringify(messageData));
    setInput("");
    setReplyingTo(null); // Clear reply after sending
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    } else if (e.key === "Escape") {
      setReplyingTo(null);
    }
  };

  const handleReply = (msg: Message) => {
    setReplyingTo(msg);
  };

  // Sidebar resize handlers
  const handleMouseDown = () => {
    setIsResizing(true);
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return;

      const minWidth = 200;
      const maxWidth = 500;
      const newWidth = Math.max(minWidth, Math.min(maxWidth, e.clientX));

      setSidebarWidth(newWidth);
      localStorage.setItem("visa-chat-sidebar-width", newWidth.toString());
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
    }

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isResizing]);

  const handleDoubleClickDivider = () => {
    // Reset to default width
    setSidebarWidth(280);
    localStorage.setItem("visa-chat-sidebar-width", "280");
  };

  const formatTime = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      const now = new Date();
      const isToday = date.toDateString() === now.toDateString();

      if (isToday) {
        return date.toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        });
      } else {
        return (
          date.toLocaleDateString([], {
            month: "short",
            day: "numeric",
          }) +
          " " +
          date.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })
        );
      }
    } catch {
      return "";
    }
  };

  const getAvatarColor = (email: string) => {
    // Generate consistent color based on email
    const colors = [
      "#FF6B6B",
      "#4ECDC4",
      "#45B7D1",
      "#FFA07A",
      "#98D8C8",
      "#6C5CE7",
      "#A29BFE",
      "#FD79A8",
      "#FDCB6E",
      "#55EFC4",
    ];
    const index = email
      .split("")
      .reduce((acc, char) => acc + char.charCodeAt(0), 0);
    return colors[index % colors.length];
  };

  return (
    <Box
      sx={{ display: "flex", height: "100%", bgcolor: "background.default" }}
    >
      {/* Online Users Sidebar - LEFT SIDE (Telegram Style) */}
      <Paper
        elevation={0}
        sx={{
          width: sidebarWidth,
          minWidth: 200,
          maxWidth: 500,
          borderRight: 1,
          borderColor: "divider",
          display: "flex",
          flexDirection: "column",
          bgcolor: "background.paper",
          position: "relative",
          transition: isResizing ? "none" : "width 0.2s ease",
        }}
      >
        {/* Sidebar Header */}
        <Box
          sx={{
            p: 2,
            borderBottom: 1,
            borderColor: "divider",
          }}
        >
          <Typography variant="subtitle1" fontWeight={600}>
            Members
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {onlineUsers.length} online
          </Typography>
        </Box>

        {/* Users List */}
        <List sx={{ flexGrow: 1, overflowY: "auto", p: 0 }}>
          {onlineUsers.length === 0 ? (
            <Box sx={{ p: 3, textAlign: "center" }}>
              <Typography variant="body2" color="text.secondary">
                No members online
              </Typography>
            </Box>
          ) : (
            onlineUsers.map((user, index) => {
              const isCurrentUser = user.email === userEmail;
              return (
                <Box key={user.email}>
                  <ListItem
                    sx={{
                      py: 1.5,
                      px: 2,
                      bgcolor: isCurrentUser
                        ? "action.selected"
                        : "transparent",
                      "&:hover": {
                        bgcolor: "action.hover",
                      },
                      cursor: "default",
                    }}
                  >
                    <ListItemAvatar sx={{ minWidth: 48 }}>
                      <Box sx={{ position: "relative" }}>
                        <Avatar
                          sx={{
                            bgcolor: getAvatarColor(user.email),
                            width: 40,
                            height: 40,
                            fontWeight: 500,
                          }}
                        >
                          {user.displayName.charAt(0).toUpperCase()}
                        </Avatar>
                        <Box
                          sx={{
                            position: "absolute",
                            bottom: 0,
                            right: 0,
                            width: 12,
                            height: 12,
                            borderRadius: "50%",
                            bgcolor: "success.main",
                            border: 2,
                            borderColor: "background.paper",
                          }}
                        />
                      </Box>
                    </ListItemAvatar>
                    <ListItemText
                      primary={
                        <Box
                          sx={{
                            display: "flex",
                            alignItems: "center",
                            gap: 0.5,
                          }}
                        >
                          <Typography
                            variant="body2"
                            fontWeight={isCurrentUser ? 600 : 500}
                            sx={{
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              whiteSpace: "nowrap",
                            }}
                          >
                            {user.displayName}
                          </Typography>
                          {isCurrentUser && (
                            <Typography
                              variant="caption"
                              color="primary"
                              sx={{ fontWeight: 500 }}
                            >
                              (You)
                            </Typography>
                          )}
                        </Box>
                      }
                      secondary={
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          sx={{
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                            display: "block",
                          }}
                        >
                          {user.email}
                        </Typography>
                      }
                    />
                  </ListItem>
                  {index < onlineUsers.length - 1 && (
                    <Divider variant="inset" component="li" />
                  )}
                </Box>
              );
            })
          )}
        </List>

        {/* Footer Info */}
        <Box
          sx={{
            p: 2,
            borderTop: 1,
            borderColor: "divider",
            bgcolor: "action.hover",
          }}
        >
          <Box sx={{ display: "flex", alignItems: "flex-start", gap: 1 }}>
            <InfoIcon fontSize="small" color="info" sx={{ mt: 0.25 }} />
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ lineHeight: 1.4 }}
            >
              Real-time messaging. All messages are visible to online members.
            </Typography>
          </Box>
        </Box>

        {/* Resize Handle */}
        <Box
          onMouseDown={handleMouseDown}
          onDoubleClick={handleDoubleClickDivider}
          sx={{
            position: "absolute",
            top: 0,
            right: -4,
            width: 8,
            height: "100%",
            cursor: "col-resize",
            zIndex: 10,
            transition: "background-color 0.2s",
            "&:hover": {
              bgcolor: "primary.main",
            },
            "&:active": {
              bgcolor: "primary.dark",
            },
          }}
        >
          {/* Visual indicator on hover */}
          <Box
            sx={{
              position: "absolute",
              top: "50%",
              left: "50%",
              transform: "translate(-50%, -50%)",
              width: 4,
              height: 40,
              borderRadius: 2,
              bgcolor: isResizing ? "primary.main" : "transparent",
              transition: "background-color 0.2s",
            }}
          />
        </Box>
      </Paper>

      {/* Main Chat Area - RIGHT SIDE */}
      <Box sx={{ flexGrow: 1, display: "flex", flexDirection: "column" }}>
        {/* Chat Header */}
        <Paper
          elevation={0}
          sx={{
            p: 2,
            borderBottom: 1,
            borderColor: "divider",
            bgcolor: "background.paper",
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
            <Box
              sx={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                bgcolor: isConnected ? "success.main" : "error.main",
              }}
            />
            <Typography variant="h6" fontWeight={500}>
              Community Chat
            </Typography>
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{ ml: "auto" }}
            >
              {onlineUsers.length}{" "}
              {onlineUsers.length === 1 ? "member" : "members"} online
            </Typography>
          </Box>
        </Paper>

        {/* Connection Status */}
        {!isConnected && (
          <Alert
            severity={isConnecting ? "info" : "warning"}
            icon={isConnecting ? <CircularProgress size={20} /> : undefined}
            sx={{ borderRadius: 0 }}
          >
            {isConnecting
              ? "Connecting to chat..."
              : "Disconnected from chat. Reconnecting..."}
          </Alert>
        )}

        {/* Messages Area */}
        <Box
          sx={{
            flexGrow: 1,
            overflowY: "auto",
            overflowX: "hidden",
            px: 2,
            py: 1,
            bgcolor: "background.default",
            "&::-webkit-scrollbar": {
              width: "8px",
            },
            "&::-webkit-scrollbar-track": {
              bgcolor: "transparent",
            },
            "&::-webkit-scrollbar-thumb": {
              bgcolor: "action.hover",
              borderRadius: "4px",
              "&:hover": {
                bgcolor: "action.selected",
              },
            },
          }}
        >
          {messages.length === 0 ? (
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                height: "100%",
                textAlign: "center",
                color: "text.secondary",
              }}
            >
              <InfoIcon sx={{ fontSize: 48, mb: 2, opacity: 0.3 }} />
              <Typography variant="h6" color="text.secondary" gutterBottom>
                No messages yet
              </Typography>
              <Typography variant="body2" color="text.disabled">
                Start the conversation!
              </Typography>
            </Box>
          ) : (
            <Box sx={{ py: 1 }}>
              {messages.map((msg, index) => {
                const isCurrentUser = msg.userEmail === userEmail;
                const isSystem = msg.type === "system";
                const showAvatar =
                  index === 0 ||
                  messages[index - 1].userEmail !== msg.userEmail;

                if (isSystem) {
                  return (
                    <Box
                      key={index}
                      sx={{
                        display: "flex",
                        justifyContent: "center",
                        my: 2,
                      }}
                    >
                      <Box
                        sx={{
                          bgcolor: "action.hover",
                          px: 2,
                          py: 0.5,
                          borderRadius: 1,
                        }}
                      >
                        <Typography variant="caption" color="text.secondary">
                          {msg.message}
                        </Typography>
                      </Box>
                    </Box>
                  );
                }

                return (
                  <Box
                    key={msg.id || index}
                    sx={{
                      display: "flex",
                      flexDirection: isCurrentUser ? "row-reverse" : "row",
                      gap: 1,
                      mb: 0.5,
                      alignItems: "flex-start",
                      "&:hover .reply-button": {
                        opacity: 1,
                      },
                    }}
                  >
                    {/* Avatar - always present to maintain alignment */}
                    <Avatar
                      sx={{
                        width: 32,
                        height: 32,
                        bgcolor: getAvatarColor(msg.userEmail),
                        fontSize: "0.875rem",
                        fontWeight: 500,
                        visibility: showAvatar ? "visible" : "hidden",
                      }}
                    >
                      {msg.displayName.charAt(0).toUpperCase()}
                    </Avatar>

                    <Box
                      sx={{
                        flexGrow: 1,
                        maxWidth: "calc(100% - 48px)",
                        display: "flex",
                        flexDirection: "column",
                        alignItems: isCurrentUser ? "flex-end" : "flex-start",
                        position: "relative",
                      }}
                    >
                      {/* Sender name - only for first in sequence */}
                      {showAvatar && (
                        <Typography
                          variant="caption"
                          sx={{
                            mb: 0.25,
                            color: getAvatarColor(msg.userEmail),
                            fontWeight: 600,
                          }}
                        >
                          {msg.displayName}
                          {isCurrentUser && (
                            <Typography
                              component="span"
                              variant="caption"
                              sx={{ ml: 0.5, opacity: 0.7 }}
                            >
                              (You)
                            </Typography>
                          )}
                        </Typography>
                      )}

                      {/* Message bubble */}
                      <Box
                        sx={{
                          position: "relative",
                        }}
                      >
                        <Box
                          sx={{
                            px: 2,
                            py: 1,
                            bgcolor: isCurrentUser
                              ? "primary.main"
                              : "background.paper",
                            color: isCurrentUser
                              ? "primary.contrastText"
                              : "text.primary",
                            borderRadius: "8px",
                            boxShadow: (theme) =>
                              theme.palette.mode === "dark"
                                ? "0 1px 2px rgba(0,0,0,0.3)"
                                : "0 1px 2px rgba(0,0,0,0.1)",
                            border: 1,
                            borderColor: isCurrentUser
                              ? "primary.main"
                              : "divider",
                          }}
                        >
                          {/* Reply preview */}
                          {msg.replyTo && (
                            <Box
                              sx={{
                                mb: 0.5,
                                pl: 1,
                                py: 0.5,
                                borderLeft: 3,
                                borderColor: isCurrentUser
                                  ? "rgba(255,255,255,0.5)"
                                  : "primary.main",
                                bgcolor: isCurrentUser
                                  ? "rgba(0,0,0,0.15)"
                                  : "action.hover",
                                borderRadius: 1,
                              }}
                            >
                              <Typography
                                variant="caption"
                                sx={{
                                  fontWeight: 600,
                                  color: isCurrentUser
                                    ? "rgba(255,255,255,0.95)"
                                    : "primary.main",
                                  display: "block",
                                }}
                              >
                                {msg.replyTo.displayName}
                              </Typography>
                              <Typography
                                variant="caption"
                                sx={{
                                  color: isCurrentUser
                                    ? "rgba(255,255,255,0.8)"
                                    : "text.secondary",
                                  display: "block",
                                  overflow: "hidden",
                                  textOverflow: "ellipsis",
                                  whiteSpace: "nowrap",
                                }}
                              >
                                {msg.replyTo.message}
                              </Typography>
                            </Box>
                          )}

                          {/* Image message */}
                          {msg.imageUrl && (
                            <Box
                              sx={{
                                mb: msg.message ? 1 : 0,
                                maxWidth: "250px",
                                borderRadius: 2,
                                overflow: "hidden",
                                cursor: "pointer",
                                "&:hover": {
                                  opacity: 0.9,
                                },
                              }}
                              onClick={() =>
                                window.open(msg.imageUrl, "_blank")
                              }
                            >
                              <img
                                src={msg.imageUrl}
                                alt="Shared image"
                                loading="lazy"
                                style={{
                                  width: "100%",
                                  height: "auto",
                                  display: "block",
                                }}
                              />
                            </Box>
                          )}

                          {/* Text message */}
                          {msg.message && (
                            <Typography
                              variant="body2"
                              sx={{
                                whiteSpace: "pre-wrap",
                                wordBreak: "break-word",
                                lineHeight: 1.5,
                              }}
                            >
                              {msg.message}
                            </Typography>
                          )}

                          {/* Timestamp */}
                          <Typography
                            variant="caption"
                            sx={{
                              display: "block",
                              mt: 0.25,
                              opacity: 0.65,
                              fontSize: "0.7rem",
                              textAlign: "right",
                            }}
                          >
                            {formatTime(msg.timestamp)}
                          </Typography>
                        </Box>

                        {/* Reply button (shows on hover) */}
                        <IconButton
                          className="reply-button"
                          size="small"
                          onClick={() => handleReply(msg)}
                          sx={{
                            position: "absolute",
                            top: -8,
                            right: isCurrentUser ? undefined : -32,
                            left: isCurrentUser ? -32 : undefined,
                            opacity: 0,
                            transition: "opacity 0.2s",
                            bgcolor: "background.paper",
                            border: 1,
                            borderColor: "divider",
                            "&:hover": {
                              bgcolor: "action.hover",
                            },
                            width: 28,
                            height: 28,
                          }}
                        >
                          <ReplyIcon sx={{ fontSize: 16 }} />
                        </IconButton>
                      </Box>
                    </Box>
                  </Box>
                );
              })}
              <div ref={messagesEndRef} />
            </Box>
          )}
        </Box>

        {/* Reply Bar */}
        {replyingTo && (
          <Paper
            elevation={0}
            sx={{
              px: 2,
              py: 1,
              borderTop: 1,
              borderColor: "divider",
              bgcolor: "action.hover",
            }}
          >
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <ReplyIcon sx={{ fontSize: 20, color: "primary.main" }} />
              <Box sx={{ flexGrow: 1 }}>
                <Typography variant="caption" fontWeight={600} color="primary">
                  Replying to {replyingTo.displayName}
                </Typography>
                <Typography
                  variant="caption"
                  display="block"
                  sx={{
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    color: "text.secondary",
                  }}
                >
                  {replyingTo.message}
                </Typography>
              </Box>
              <IconButton size="small" onClick={() => setReplyingTo(null)}>
                <CloseIcon fontSize="small" />
              </IconButton>
            </Box>
          </Paper>
        )}

        {/* Image Preview */}
        {imagePreview && (
          <Paper
            elevation={0}
            sx={{
              px: 2,
              py: 1,
              borderTop: 1,
              borderColor: "divider",
              bgcolor: "action.hover",
            }}
          >
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <ImageIcon sx={{ fontSize: 20, color: "primary.main" }} />
              <Box sx={{ position: "relative" }}>
                <img
                  src={imagePreview}
                  alt="Preview"
                  style={{
                    maxWidth: "150px",
                    maxHeight: "100px",
                    borderRadius: "8px",
                    objectFit: "cover",
                  }}
                />
              </Box>
              <IconButton
                size="small"
                onClick={() => {
                  setSelectedImage(null);
                  setImagePreview(null);
                }}
              >
                <CloseIcon fontSize="small" />
              </IconButton>
            </Box>
          </Paper>
        )}

        {/* Input Area */}
        <Paper
          elevation={0}
          sx={{
            p: 2,
            borderTop: 1,
            borderColor: "divider",
            bgcolor: "background.paper",
          }}
        >
          <Box sx={{ display: "flex", gap: 1, alignItems: "flex-end" }}>
            {/* Hidden file input */}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              style={{ display: "none" }}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleImageSelect(file);
              }}
            />

            {/* Image upload button */}
            <IconButton
              color="primary"
              onClick={() => fileInputRef.current?.click()}
              disabled={!isConnected || isUploading}
              title="Attach image (or paste screenshot)"
            >
              <AttachFileIcon />
            </IconButton>

            <TextField
              fullWidth
              placeholder={
                imagePreview
                  ? "Add a caption (optional)..."
                  : replyingTo
                  ? "Type your reply..."
                  : "Type a message or paste an image..."
              }
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyPress}
              disabled={!isConnected}
              multiline
              maxRows={4}
              variant="outlined"
              size="small"
              sx={{
                "& .MuiOutlinedInput-root": {
                  borderRadius: 3,
                  bgcolor: "background.default",
                },
              }}
            />
            <IconButton
              color="primary"
              onClick={sendMessage}
              disabled={
                (!input.trim() && !selectedImage) || !isConnected || isUploading
              }
              size="large"
              sx={{
                bgcolor:
                  (input.trim() || selectedImage) && isConnected
                    ? "primary.main"
                    : "action.disabledBackground",
                color: "white",
                "&:hover": {
                  bgcolor: "primary.dark",
                },
                "&:disabled": {
                  bgcolor: "action.disabledBackground",
                  color: "action.disabled",
                },
                width: 44,
                height: 44,
              }}
            >
              {isUploading ? (
                <CircularProgress size={24} color="inherit" />
              ) : (
                <SendIcon />
              )}
            </IconButton>
          </Box>
        </Paper>
      </Box>
    </Box>
  );
}
