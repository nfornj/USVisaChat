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
  ListItemButton,
  Alert,
  CircularProgress,
  Divider,
  ToggleButton,
  ToggleButtonGroup,
  Snackbar,
  Drawer,
  Badge,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import {
  Send as SendIcon,
  Info as InfoIcon,
  Reply as ReplyIcon,
  Close as CloseIcon,
  Image as ImageIcon,
  AttachFile as AttachFileIcon,
  ArrowBack as ArrowBackIcon,
  Edit as EditIcon,
  Check as CheckIcon,
  Group as GroupIcon,
  FormatListBulleted as ListIcon,
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
  topicId?: string | null; // For thread segregation
  edited?: boolean; // For edited messages
}

interface OnlineUser {
  email: string;
  displayName: string;
}

interface CommunityChatProps {
  userEmail: string;
  displayName: string;
  onOnlineCountChange: (count: number) => void;
  roomId?: string; // Article/topic ID for room isolation
  roomName?: string; // Article/topic name for display
  onBackToTopics?: () => void; // Callback to go back to topics list
}

export default function CommunityChat({
  userEmail,
  displayName,
  onOnlineCountChange,
  roomId = "general",
  roomName = "General Discussion",
  onBackToTopics,
}: CommunityChatProps) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [onlineUsers, setOnlineUsers] = useState<OnlineUser[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(true);
  const [replyingTo, setReplyingTo] = useState<Message | null>(null);

  // Edit message state
  const [editingMessageId, setEditingMessageId] = useState<
    string | number | null
  >(null);
  const [editContent, setEditContent] = useState("");

  // Snackbar state for error/success messages
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: "success" | "error" | "info";
  }>({
    open: false,
    message: "",
    severity: "info",
  });

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

  // Right-side Questions panel width and resize
  const [questionsWidth, setQuestionsWidth] = useState(() => {
    const saved = localStorage.getItem("visa-chat-questions-width");
    return saved ? parseInt(saved, 10) : 320;
  });
  const [isResizingQuestions, setIsResizingQuestions] = useState(false);
  const resizeQuestionsStartX = useRef<number>(0);
  const resizeQuestionsStartWidth = useRef<number>(questionsWidth);

  // Compose mode and questions/jump state
  const [composeMode, setComposeMode] = useState<"auto" | "question" | "info">(
    "auto"
  );
  const messageRefs = useRef<Record<string | number, HTMLDivElement | null>>(
    {}
  );
  // Topic/thread selection
  const [selectedTopicId, setSelectedTopicId] = useState<
    string | number | null
  >(null);

  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const previousDisplayNameRef = useRef<string>(displayName);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  // Mobile drawers visibility
  const [openMembersDrawer, setOpenMembersDrawer] = useState(false);
  const [openTopicsDrawer, setOpenTopicsDrawer] = useState(false);

  console.log("Connected as:", displayName, userEmail);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // WebSocket connection - reconnect when roomId changes
  useEffect(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${
      window.location.host
    }/ws/chat?user_email=${encodeURIComponent(
      userEmail
    )}&display_name=${encodeURIComponent(
      displayName
    )}&room_id=${encodeURIComponent(roomId)}`;

    console.log(
      "Connecting to WebSocket:",
      wsUrl,
      "as",
      displayName,
      "room:",
      roomId
    );
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
          setMessages(
            (data.messages || []).map((m: any) => ({
              ...m,
              messageType: m.messageType,
            }))
          );
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
              messageType: data.messageType,
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
  }, [userEmail, roomId, onOnlineCountChange]);

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
      messageType: classifyMessageType(input.trim() || ""),
    };

    // Include reply information if replying or topic selected
    if (replyingTo) {
      messageData.replyTo = replyingTo.id;
    } else if (selectedTopicId) {
      messageData.replyTo = selectedTopicId;
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
      messageType:
        replyingTo || selectedTopicId
          ? "info"
          : classifyMessageType(input.trim()),
    };

    // Include reply information if replying
    if (replyingTo) {
      messageData.replyTo = replyingTo.id;
    } else if (selectedTopicId) {
      messageData.replyTo = selectedTopicId;
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

  // Edit message functions
  const startEditingMessage = (msg: Message) => {
    setEditingMessageId(msg.id!);
    setEditContent(msg.message);
  };

  const cancelEditing = () => {
    setEditingMessageId(null);
    setEditContent("");
  };

  const saveEditedMessage = async (messageId: string | number) => {
    if (!editContent.trim()) return;

    try {
      const response = await fetch("/chat/edit-message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message_id: messageId,
          new_content: editContent.trim(),
          user_email: userEmail,
        }),
      });

      if (response.ok) {
        await response.json();
        // Update the message in local state
        setMessages((prev) =>
          prev.map((m) =>
            m.id === messageId
              ? { ...m, message: editContent.trim(), edited: true }
              : m
          )
        );
        setSnackbar({
          open: true,
          message: "Message edited successfully",
          severity: "success",
        });
        cancelEditing();
      } else {
        const error = await response.json();
        setSnackbar({
          open: true,
          message: error.detail || "Failed to edit message",
          severity: "error",
        });
      }
    } catch (error) {
      console.error("Error editing message:", error);
      setSnackbar({
        open: true,
        message: "Failed to edit message. Please try again.",
        severity: "error",
      });
    }
  };

  const canEditMessage = (msg: Message): boolean => {
    if (msg.userEmail !== userEmail) return false;
    const messageTime = new Date(msg.timestamp).getTime();
    const now = new Date().getTime();
    const minutesAgo = (now - messageTime) / 1000 / 60;
    return minutesAgo < 15; // Can edit within 15 minutes
  };

  // When replying directly to a message, also select its root topic
  // const handleReply = (msg: Message) => {
  //   setReplyingTo(msg);
  //   const rootId = findRootTopicId(msg);
  //   if (rootId) setSelectedTopicId(rootId);
  //   setTimeout(() => inputRef.current?.focus(), 0);
  // };

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

  // Questions panel resize handlers
  const handleMouseDownQuestions = (e: React.MouseEvent) => {
    setIsResizingQuestions(true);
    resizeQuestionsStartX.current = e.clientX;
    resizeQuestionsStartWidth.current = questionsWidth;
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizingQuestions) return;
      const delta = resizeQuestionsStartX.current - e.clientX;
      const minWidth = 240;
      const maxWidth = 500;
      const newWidth = Math.max(
        minWidth,
        Math.min(maxWidth, resizeQuestionsStartWidth.current + delta)
      );
      setQuestionsWidth(newWidth);
      localStorage.setItem("visa-chat-questions-width", newWidth.toString());
    };

    const handleMouseUp = () => {
      setIsResizingQuestions(false);
    };

    if (isResizingQuestions) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
    }

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isResizingQuestions]);

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

  // Classification helpers and derived questions
  const classifyMessageType = (text: string): "question" | "info" => {
    if (composeMode === "question") return "question";
    if (composeMode === "info") return "info";
    return text.trim().endsWith("?") ? "question" : "info";
  };

  const getMessageType = (m: Message): "question" | "info" => {
    if (m.messageType === "question" || m.messageType === "info")
      return m.messageType;
    return m.message?.trim().endsWith("?") ? "question" : "info";
  };

  // Build topic threads (Question/Info roots)
  const nonSystemMessages = messages.filter((m) => m.type !== "system");
  // Topics are question/info messages that are NOT replies
  const topics = nonSystemMessages.filter((m) => {
    if (m.replyTo) return false; // Replies are never root topics
    return getMessageType(m) === "question" || getMessageType(m) === "info";
  });
  const messageById: Record<string | number, Message> = {} as any;
  nonSystemMessages.forEach((m, i) => {
    const key = m.id ?? `idx-${i}`;
    (messageById as any)[key] = m;
  });
  const findRootTopicId = (msg: Message): string | number | null => {
    // If it's a reply, walk up the chain to find root topic
    if (!msg.replyTo) {
      // No replyTo, so it's a root topic itself (if it's question/info)
      if (
        getMessageType(msg) === "question" ||
        getMessageType(msg) === "info"
      ) {
        return msg.id ?? null;
      }
      return null;
    }
    let current: Message | undefined = msg;
    const guard = new Set<string | number>();
    while (current && current.replyTo) {
      const parentId: any = current.replyTo.id as any;
      if (guard.has(parentId)) break;
      guard.add(parentId);
      const parent = messageById[parentId];
      if (!parent) {
        // Parent not found in messageById, use the replyTo.id directly
        return parentId;
      }
      if (
        getMessageType(parent) === "question" ||
        getMessageType(parent) === "info"
      ) {
        return parent.id ?? null;
      }
      current = parent;
    }
    return null;
  };
  const topicThreads: Record<string | number, Message[]> = {} as any;
  topics.forEach((t) => {
    const tid = t.id ?? `topic-${t.timestamp}`;
    (topicThreads as any)[tid] = [t];
  });
  nonSystemMessages.forEach((m) => {
    const rootId = findRootTopicId(m);
    if (rootId && topicThreads[rootId]) {
      if ((topicThreads[rootId] as any)[0] !== m)
        (topicThreads[rootId] as any).push(m);
    }
  });
  const sortedTopicIds = Object.keys(topicThreads).sort((a, b) => {
    const at = new Date((topicThreads as any)[a][0].timestamp).getTime();
    const bt = new Date((topicThreads as any)[b][0].timestamp).getTime();
    return bt - at;
  });
  Object.keys(topicThreads).forEach((tid) => {
    (topicThreads as any)[tid].sort(
      (m1: Message, m2: Message) =>
        new Date(m1.timestamp).getTime() - new Date(m2.timestamp).getTime()
    );
  });

  return (
    <Box
      sx={{ display: "flex", height: "100%", bgcolor: "background.default" }}
    >
      {/* Online Users Sidebar - LEFT SIDE (hidden on mobile, Drawer used) */}
      {!isMobile && (
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
                borderRadius: 0,
                bgcolor: isResizing ? "primary.main" : "transparent",
                transition: "background-color 0.2s",
              }}
            />
          </Box>
        </Paper>
      )}

      {/* Main Chat Area - CENTER */}
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
            {isMobile && (
              <>
                <IconButton onClick={() => setOpenMembersDrawer(true)}>
                  <Badge color="primary" badgeContent={onlineUsers.length}>
                    <GroupIcon />
                  </Badge>
                </IconButton>
                <IconButton onClick={() => setOpenTopicsDrawer(true)}>
                  <ListIcon />
                </IconButton>
              </>
            )}
            {onBackToTopics && (
              <IconButton
                onClick={onBackToTopics}
                size="small"
                sx={{
                  color: "text.secondary",
                  "&:hover": {
                    color: "primary.main",
                    bgcolor: "action.hover",
                  },
                }}
              >
                <ArrowBackIcon />
              </IconButton>
            )}
            <Box
              sx={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                bgcolor: isConnected ? "success.main" : "error.main",
              }}
            />
            <Box sx={{ flex: 1 }}>
              <Typography variant="h6" fontWeight={500}>
                {roomName}
              </Typography>
              {roomId !== "general" && (
                <Typography variant="caption" color="text.secondary">
                  Article Discussion
                </Typography>
              )}
            </Box>
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

        {/* Chat Messages Area */}
        <Box
          sx={{
            flexGrow: 1,
            overflowY: "auto",
            overflowX: "hidden",
            WebkitOverflowScrolling: "touch",
            overscrollBehavior: "contain",
            scrollBehavior: "smooth",
            px: 3,
            py: 2,
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
          {sortedTopicIds.length === 0 ? (
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
                No topics yet
              </Typography>
              <Typography variant="body2" color="text.disabled">
                Start by posting a Question or Information topic.
              </Typography>
            </Box>
          ) : selectedTopicId ? (
            // TOPIC ISOLATION: Show only the selected topic's thread
            (() => {
              const thread = (topicThreads as any)[
                selectedTopicId
              ] as Message[];
              if (!thread) return null;
              const root = thread[0];
              const topicType = getMessageType(root);
              return (
                <Box sx={{ maxWidth: 900, mx: "auto", width: "100%" }}>
                  {/* Topic Header - Bold and Highlighted */}
                  <Box
                    sx={{
                      mb: 3,
                      p: 2,
                      borderRadius: 0,
                      bgcolor:
                        topicType === "question"
                          ? "rgba(251, 191, 36, 0.1)"
                          : "rgba(96, 165, 250, 0.1)",
                      border: 1,
                      borderColor:
                        topicType === "question" ? "warning.main" : "info.main",
                    }}
                  >
                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        gap: 1.5,
                        mb: 1,
                      }}
                    >
                      <Typography
                        variant="caption"
                        sx={{
                          px: 1.5,
                          py: 0.5,
                          borderRadius: 0,
                          bgcolor:
                            topicType === "question"
                              ? "warning.main"
                              : "info.main",
                          color:
                            topicType === "question"
                              ? "warning.contrastText"
                              : "info.contrastText",
                          fontWeight: 700,
                          letterSpacing: 0.5,
                          textTransform: "uppercase",
                        }}
                      >
                        {topicType === "question" ? "Question" : "Information"}
                      </Typography>
                      <Box
                        sx={{ display: "flex", alignItems: "center", gap: 1 }}
                      >
                        <Avatar
                          sx={{
                            width: 24,
                            height: 24,
                            bgcolor: getAvatarColor(root.userEmail),
                            fontSize: "0.7rem",
                          }}
                        >
                          {root.displayName.charAt(0).toUpperCase()}
                        </Avatar>
                        <Typography variant="body2" fontWeight={500}>
                          {root.displayName}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          • {formatTime(root.timestamp)}
                        </Typography>
                      </Box>
                    </Box>
                    {editingMessageId === root.id ? (
                      <Box
                        sx={{
                          display: "flex",
                          gap: 1,
                          alignItems: "flex-start",
                          mt: 1,
                        }}
                      >
                        <TextField
                          fullWidth
                          multiline
                          maxRows={6}
                          value={editContent}
                          onChange={(e) => setEditContent(e.target.value)}
                          autoFocus
                          size="small"
                          sx={{ bgcolor: "background.paper" }}
                        />
                        <IconButton
                          size="small"
                          color="primary"
                          onClick={() => saveEditedMessage(root.id!)}
                        >
                          <CheckIcon fontSize="small" />
                        </IconButton>
                        <IconButton size="small" onClick={cancelEditing}>
                          <CloseIcon fontSize="small" />
                        </IconButton>
                      </Box>
                    ) : (
                      <>
                        <Box
                          sx={{
                            display: "flex",
                            alignItems: "flex-start",
                            gap: 1,
                          }}
                        >
                          <Typography
                            variant="body1"
                            sx={{
                              fontWeight: 600,
                              color: "text.primary",
                              whiteSpace: "pre-wrap",
                              wordBreak: "break-word",
                              flex: 1,
                            }}
                          >
                            {root.message}
                          </Typography>
                          {canEditMessage(root) && (
                            <IconButton
                              size="small"
                              onClick={() => startEditingMessage(root)}
                              sx={{
                                opacity: 0.6,
                                "&:hover": { opacity: 1 },
                              }}
                            >
                              <EditIcon sx={{ fontSize: 18 }} />
                            </IconButton>
                          )}
                        </Box>
                        {root.edited && (
                          <Typography
                            variant="caption"
                            sx={{
                              display: "block",
                              mt: 0.5,
                              fontSize: "0.7rem",
                              fontStyle: "italic",
                              opacity: 0.7,
                            }}
                          >
                            (edited)
                          </Typography>
                        )}
                      </>
                    )}
                  </Box>

                  {/* Replies - Natural chat flow */}
                  <Box sx={{ pl: 2 }}>
                    {thread.slice(1).length === 0 ? (
                      <Box
                        sx={{
                          p: 3,
                          textAlign: "center",
                          bgcolor: "action.hover",
                          borderRadius: 0,
                          border: 1,
                          borderColor: "divider",
                          borderStyle: "dashed",
                        }}
                      >
                        <Typography variant="body2" color="text.secondary">
                          No replies yet. Be the first to respond!
                        </Typography>
                      </Box>
                    ) : (
                      thread.slice(1).map((msg, idx) => {
                        const isCurrentUser = msg.userEmail === userEmail;
                        const keyId =
                          msg.id ?? `${selectedTopicId}-reply-${idx}`;
                        return (
                          <Box
                            key={keyId}
                            ref={(el: HTMLDivElement | null) => {
                              messageRefs.current[keyId] = el;
                            }}
                            sx={{
                              mb: 2,
                              display: "flex",
                              gap: 1.5,
                              alignItems: "flex-start",
                            }}
                          >
                            {/* Avatar */}
                            <Avatar
                              sx={{
                                width: 32,
                                height: 32,
                                bgcolor: getAvatarColor(msg.userEmail),
                                fontSize: "0.8rem",
                                flexShrink: 0,
                              }}
                            >
                              {msg.displayName.charAt(0).toUpperCase()}
                            </Avatar>

                            {/* Message Content */}
                            <Box sx={{ flex: 1, minWidth: 0 }}>
                              {/* Name and timestamp */}
                              <Box
                                sx={{
                                  display: "flex",
                                  alignItems: "baseline",
                                  gap: 1,
                                  mb: 0.5,
                                }}
                              >
                                <Typography
                                  variant="body2"
                                  fontWeight={600}
                                  sx={{
                                    color: isCurrentUser
                                      ? "primary.main"
                                      : "text.primary",
                                  }}
                                >
                                  {msg.displayName}
                                  {isCurrentUser && (
                                    <Typography
                                      component="span"
                                      variant="caption"
                                      color="text.secondary"
                                      sx={{ ml: 0.5 }}
                                    >
                                      (You)
                                    </Typography>
                                  )}
                                </Typography>
                                <Typography
                                  variant="caption"
                                  color="text.secondary"
                                >
                                  {formatTime(msg.timestamp)}
                                </Typography>
                              </Box>

                              {/* Message bubble - transparent/natural */}
                              <Box
                                sx={{
                                  px: 1.5,
                                  py: 1,
                                  bgcolor: "transparent",
                                  borderRadius: 0,
                                  position: "relative",
                                }}
                              >
                                {msg.imageUrl && (
                                  <Box
                                    sx={{
                                      mb: msg.message ? 1 : 0,
                                      maxWidth: "400px",
                                      borderRadius: 0,
                                      overflow: "hidden",
                                      cursor: "pointer",
                                      border: 1,
                                      borderColor: "divider",
                                      "&:hover": { opacity: 0.9 },
                                    }}
                                    onClick={() =>
                                      window.open(msg.imageUrl!, "_blank")
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
                                {msg.message && (
                                  <>
                                    {editingMessageId === msg.id ? (
                                      <Box
                                        sx={{
                                          display: "flex",
                                          gap: 1,
                                          alignItems: "flex-start",
                                        }}
                                      >
                                        <TextField
                                          fullWidth
                                          multiline
                                          maxRows={6}
                                          value={editContent}
                                          onChange={(e) =>
                                            setEditContent(e.target.value)
                                          }
                                          autoFocus
                                          size="small"
                                          sx={{ bgcolor: "background.paper" }}
                                        />
                                        <IconButton
                                          size="small"
                                          color="primary"
                                          onClick={() =>
                                            saveEditedMessage(msg.id!)
                                          }
                                        >
                                          <CheckIcon fontSize="small" />
                                        </IconButton>
                                        <IconButton
                                          size="small"
                                          onClick={cancelEditing}
                                        >
                                          <CloseIcon fontSize="small" />
                                        </IconButton>
                                      </Box>
                                    ) : (
                                      <>
                                        <Box
                                          sx={{
                                            display: "flex",
                                            alignItems: "flex-start",
                                            gap: 1,
                                          }}
                                        >
                                          <Typography
                                            variant="body2"
                                            sx={{
                                              whiteSpace: "pre-wrap",
                                              wordBreak: "break-word",
                                              lineHeight: 1.6,
                                              color: "text.primary",
                                              flex: 1,
                                            }}
                                          >
                                            {msg.message}
                                          </Typography>
                                          {canEditMessage(msg) && (
                                            <IconButton
                                              size="small"
                                              onClick={() =>
                                                startEditingMessage(msg)
                                              }
                                              sx={{
                                                opacity: 0.6,
                                                "&:hover": { opacity: 1 },
                                              }}
                                            >
                                              <EditIcon sx={{ fontSize: 16 }} />
                                            </IconButton>
                                          )}
                                        </Box>
                                        {msg.edited && (
                                          <Typography
                                            variant="caption"
                                            sx={{
                                              display: "block",
                                              mt: 0.5,
                                              fontSize: "0.7rem",
                                              fontStyle: "italic",
                                              opacity: 0.7,
                                            }}
                                          >
                                            (edited)
                                          </Typography>
                                        )}
                                      </>
                                    )}
                                  </>
                                )}
                              </Box>
                            </Box>
                          </Box>
                        );
                      })
                    )}
                  </Box>
                  <div ref={messagesEndRef} />
                </Box>
              );
            })()
          ) : (
            // Show all topics overview (no topic selected)
            <Box sx={{ maxWidth: 900, mx: "auto", width: "100%" }}>
              {sortedTopicIds.map((tid) => {
                const thread = (topicThreads as any)[tid] as Message[];
                const root = thread[0];
                const topicType = getMessageType(root);
                const replyCount = thread.length - 1;
                return (
                  <Paper
                    key={tid}
                    elevation={0}
                    onClick={() => {
                      setSelectedTopicId(root.id ?? tid);
                      setTimeout(() => inputRef.current?.focus(), 0);
                    }}
                    sx={{
                      mb: 2,
                      p: 2,
                      border: 1,
                      borderColor: "divider",
                      borderRadius: 0,
                      cursor: "pointer",
                      transition: "all 0.2s ease",
                      "&:hover": {
                        borderColor: "primary.main",
                        bgcolor: "action.hover",
                        transform: "translateY(-2px)",
                        boxShadow: 2,
                      },
                    }}
                  >
                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "flex-start",
                        gap: 1.5,
                      }}
                    >
                      <Avatar
                        sx={{
                          width: 40,
                          height: 40,
                          bgcolor: getAvatarColor(root.userEmail),
                        }}
                      >
                        {root.displayName.charAt(0).toUpperCase()}
                      </Avatar>
                      <Box sx={{ flex: 1, minWidth: 0 }}>
                        <Box
                          sx={{
                            display: "flex",
                            alignItems: "center",
                            gap: 1,
                            mb: 0.5,
                          }}
                        >
                          <Typography
                            variant="caption"
                            sx={{
                              px: 1,
                              py: 0.25,
                              borderRadius: 0,
                              bgcolor:
                                topicType === "question"
                                  ? "warning.main"
                                  : "info.main",
                              color:
                                topicType === "question"
                                  ? "warning.contrastText"
                                  : "info.contrastText",
                              fontWeight: 700,
                              letterSpacing: 0.5,
                              textTransform: "uppercase",
                            }}
                          >
                            {topicType === "question" ? "Q" : "INFO"}
                          </Typography>
                          <Typography variant="body2" fontWeight={600}>
                            {root.displayName}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            • {formatTime(root.timestamp)}
                          </Typography>
                        </Box>
                        <Typography
                          variant="body1"
                          sx={{
                            fontWeight: 500,
                            mb: 0.5,
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            display: "-webkit-box",
                            WebkitLineClamp: 2,
                            WebkitBoxOrient: "vertical",
                          }}
                        >
                          {root.message}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {replyCount === 0
                            ? "No replies yet"
                            : `${replyCount} ${
                                replyCount === 1 ? "reply" : "replies"
                              }`}
                        </Typography>
                      </Box>
                    </Box>
                  </Paper>
                );
              })}
            </Box>
          )}
        </Box>

        {/* Back to Topics Button */}
        {selectedTopicId && (
          <Paper
            elevation={0}
            sx={{
              px: 2,
              py: 1.5,
              borderTop: 1,
              borderBottom: 1,
              borderColor: "divider",
              bgcolor: "background.paper",
            }}
          >
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1,
                cursor: "pointer",
                transition: "color 0.2s",
                "&:hover": { color: "primary.main" },
              }}
              onClick={() => setSelectedTopicId(null)}
            >
              <ArrowBackIcon fontSize="small" />
              <Typography variant="body2" fontWeight={500}>
                Back to all topics
              </Typography>
            </Box>
          </Paper>
        )}

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
            pb: "calc(16px + env(safe-area-inset-bottom))",
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

            {/* Compose mode toggle */}
            <ToggleButtonGroup
              value={composeMode}
              exclusive
              size="small"
              onChange={(_, v) => {
                if (v) setComposeMode(v);
              }}
              sx={{ alignSelf: "flex-end" }}
            >
              <ToggleButton value="auto">Auto</ToggleButton>
              <ToggleButton value="question">Question</ToggleButton>
              <ToggleButton value="info">Info</ToggleButton>
            </ToggleButtonGroup>

            <TextField
              inputRef={inputRef}
              fullWidth
              placeholder={
                imagePreview
                  ? "Add a caption (optional)..."
                  : replyingTo
                  ? "Reply to this message..."
                  : selectedTopicId
                  ? "Reply to this topic..."
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

      {/* Topics Panel - RIGHT SIDE (hidden on mobile, Drawer used) */}
      {!isMobile && (
        <Paper
          elevation={0}
          sx={{
            width: questionsWidth,
            minWidth: 240,
            maxWidth: 500,
            borderLeft: 1,
            borderColor: "divider",
            display: "flex",
            flexDirection: "column",
            bgcolor: "background.paper",
            position: "relative",
            flexShrink: 0,
            transition: isResizingQuestions ? "none" : "width 0.2s ease",
          }}
        >
          <Box
            sx={{
              p: 2,
              borderBottom: 1,
              borderColor: "divider",
            }}
          >
            <Typography variant="subtitle1" fontWeight={600}>
              Topics
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {sortedTopicIds.length} total
            </Typography>
          </Box>

          <List sx={{ flexGrow: 1, overflowY: "auto", p: 0 }}>
            {sortedTopicIds.length === 0 ? (
              <Box sx={{ p: 3, textAlign: "center" }}>
                <Typography variant="body2" color="text.secondary">
                  No topics yet
                </Typography>
              </Box>
            ) : (
              sortedTopicIds.map((tid, i) => {
                const thread = (topicThreads as any)[tid] as Message[];
                const q = thread[0];
                const key = q.id ?? i;
                const tType = getMessageType(q);
                return (
                  <ListItem key={key} disablePadding>
                    <ListItemButton
                      onClick={() => {
                        setSelectedTopicId(q.id ?? tid);
                      }}
                      sx={{ alignItems: "flex-start", py: 1.25 }}
                    >
                      <ListItemAvatar>
                        <Avatar
                          sx={{
                            bgcolor: getAvatarColor(q.userEmail),
                            width: 32,
                            height: 32,
                          }}
                        >
                          {q.displayName.charAt(0).toUpperCase()}
                        </Avatar>
                      </ListItemAvatar>
                      <ListItemText
                        primary={
                          <Box
                            sx={{
                              display: "flex",
                              alignItems: "center",
                              gap: 1,
                            }}
                          >
                            <Typography
                              variant="caption"
                              sx={{
                                px: 0.75,
                                py: 0.25,
                                borderRadius: 1,
                                bgcolor:
                                  tType === "question"
                                    ? "warning.main"
                                    : "info.main",
                                color:
                                  tType === "question"
                                    ? "warning.contrastText"
                                    : "info.contrastText",
                                fontWeight: 700,
                                letterSpacing: 0.5,
                              }}
                            >
                              {tType === "question" ? "Q" : "Info"}
                            </Typography>
                            <Typography
                              variant="body2"
                              sx={{
                                fontWeight: 700,
                                overflow: "hidden",
                                textOverflow: "ellipsis",
                                whiteSpace: "nowrap",
                                flex: 1,
                              }}
                            >
                              {q.message}
                            </Typography>
                          </Box>
                        }
                        secondary={
                          <Typography variant="caption" color="text.secondary">
                            {thread.length - 1} repl
                            {thread.length - 1 === 1 ? "y" : "ies"} •{" "}
                            {q.displayName} • {formatTime(q.timestamp)}
                          </Typography>
                        }
                      />
                    </ListItemButton>
                  </ListItem>
                );
              })
            )}
          </List>

          {/* Resize Handle (left edge of panel) */}
          <Box
            onMouseDown={handleMouseDownQuestions}
            sx={{
              position: "absolute",
              top: 0,
              left: -4,
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
            <Box
              sx={{
                position: "absolute",
                top: "50%",
                left: "50%",
                transform: "translate(-50%, -50%)",
                width: 4,
                height: 40,
                borderRadius: 2,
                bgcolor: isResizingQuestions ? "primary.main" : "transparent",
                transition: "background-color 0.2s",
              }}
            />
          </Box>
        </Paper>
      )}

      {/* Mobile Drawers */}
      {isMobile && (
        <>
          <Drawer
            open={openMembersDrawer}
            onClose={() => setOpenMembersDrawer(false)}
            PaperProps={{
              sx: { width: Math.min(320, window.innerWidth - 56) },
            }}
          >
            <Box
              sx={{
                width: 1,
                height: 1,
                display: "flex",
                flexDirection: "column",
              }}
            >
              {/* Reuse Members sidebar content */}
              {/* We embed a minimal version: */}
              <Box sx={{ p: 2, borderBottom: 1, borderColor: "divider" }}>
                <Typography variant="subtitle1" fontWeight={600}>
                  Members
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {onlineUsers.length} online
                </Typography>
              </Box>
              <List sx={{ flexGrow: 1, overflowY: "auto", p: 0 }}>
                {onlineUsers.map((user) => (
                  <ListItem key={user.email}>
                    <ListItemAvatar>
                      <Avatar sx={{ bgcolor: getAvatarColor(user.email) }}>
                        {user.displayName.charAt(0).toUpperCase()}
                      </Avatar>
                    </ListItemAvatar>
                    <ListItemText
                      primary={user.displayName}
                      secondary={user.email}
                    />
                  </ListItem>
                ))}
              </List>
            </Box>
          </Drawer>
          <Drawer
            anchor="right"
            open={openTopicsDrawer}
            onClose={() => setOpenTopicsDrawer(false)}
            PaperProps={{
              sx: { width: Math.min(360, window.innerWidth - 56) },
            }}
          >
            <Box
              sx={{
                width: 1,
                height: 1,
                display: "flex",
                flexDirection: "column",
              }}
            >
              <Box sx={{ p: 2, borderBottom: 1, borderColor: "divider" }}>
                <Typography variant="subtitle1" fontWeight={600}>
                  Topics
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {sortedTopicIds.length} total
                </Typography>
              </Box>
              <List sx={{ flexGrow: 1, overflowY: "auto", p: 0 }}>
                {sortedTopicIds.map((tid, i) => {
                  const thread = (topicThreads as any)[tid] as Message[];
                  const q = thread[0];
                  const key = q.id ?? i;
                  const tType = getMessageType(q);
                  return (
                    <ListItem key={key} disablePadding>
                      <ListItemButton
                        onClick={() => {
                          setSelectedTopicId(q.id ?? tid);
                          setOpenTopicsDrawer(false);
                        }}
                        sx={{ alignItems: "flex-start", py: 1.25 }}
                      >
                        <ListItemAvatar>
                          <Avatar sx={{ bgcolor: getAvatarColor(q.userEmail) }}>
                            {q.displayName.charAt(0).toUpperCase()}
                          </Avatar>
                        </ListItemAvatar>
                        <ListItemText
                          primary={
                            <Box
                              sx={{
                                display: "flex",
                                alignItems: "center",
                                gap: 1,
                              }}
                            >
                              <Typography
                                variant="caption"
                                sx={{
                                  px: 0.75,
                                  py: 0.25,
                                  borderRadius: 1,
                                  bgcolor:
                                    tType === "question"
                                      ? "warning.main"
                                      : "info.main",
                                  color:
                                    tType === "question"
                                      ? "warning.contrastText"
                                      : "info.contrastText",
                                  fontWeight: 700,
                                  letterSpacing: 0.5,
                                }}
                              >
                                {" "}
                                {tType === "question" ? "Q" : "Info"}{" "}
                              </Typography>
                              <Typography
                                variant="body2"
                                sx={{
                                  fontWeight: 700,
                                  overflow: "hidden",
                                  textOverflow: "ellipsis",
                                  whiteSpace: "nowrap",
                                  flex: 1,
                                }}
                              >
                                {q.message}
                              </Typography>
                            </Box>
                          }
                          secondary={
                            <Typography
                              variant="caption"
                              color="text.secondary"
                            >
                              {thread.length - 1} repl
                              {thread.length - 1 === 1 ? "y" : "ies"} •{" "}
                              {q.displayName} • {formatTime(q.timestamp)}
                            </Typography>
                          }
                        />
                      </ListItemButton>
                    </ListItem>
                  );
                })}
              </List>
            </Box>
          </Drawer>
        </>
      )}

      {/* Snackbar for error/success messages */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        <Alert
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          severity={snackbar.severity}
          variant="filled"
          sx={{ width: "100%" }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
