import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  TrendingUp,
  Users,
  MessageCircle,
  ArrowRight,
  Zap,
  Sparkles,
  Stamp,
  DollarSign,
  FileText,
  GraduationCap,
  Clock,
  MessageSquare,
  Calendar,
  CheckCircle,
} from "lucide-react";
import { useTheme } from "@mui/material/styles";
import { Box } from "@mui/material";
import axios from "axios";

interface Topic {
  id: string;
  name: string;
  category: string;
  activeUsers: number;
  messageCount: number;
  lastActive: string;
  trend: "hot" | "rising" | "steady";
  gradient: string;
  icon: React.ReactNode;
}

interface TopicsHomeProps {
  onTopicSelect: (topicId: string, topicName: string) => void;
}

const TopicsHome: React.FC<TopicsHomeProps> = ({ onTopicSelect }) => {
  const theme = useTheme();
  const isDark = theme.palette.mode === "dark";

  // Room statistics from API
  const [roomStats, setRoomStats] = useState<Record<string, { online_users: number; message_count: number }>>({});

  const [topics] = useState<Topic[]>([
    {
      id: "h1b-stamping",
      name: "H1B Visa Stamping",
      category: "Work Visa",
      activeUsers: 156,
      messageCount: 3420,
      lastActive: "2m ago",
      trend: "hot",
      gradient: "from-orange-400 to-red-500",
      icon: <Stamp className="w-full h-full" />,
    },
    {
      id: "h1b-fee-hike",
      name: "H1B Fee Hike 2025",
      category: "Policy Update",
      activeUsers: 89,
      messageCount: 1245,
      lastActive: "5m ago",
      trend: "hot",
      gradient: "from-purple-400 to-pink-500",
      icon: <DollarSign className="w-full h-full" />,
    },
    {
      id: "dropbox-eligibility",
      name: "Dropbox Eligibility",
      category: "Process",
      activeUsers: 67,
      messageCount: 892,
      lastActive: "8m ago",
      trend: "rising",
      gradient: "from-blue-400 to-cyan-500",
      icon: <FileText className="w-full h-full" />,
    },
    {
      id: "f1-visa",
      name: "F1 Student Visa",
      category: "Student Visa",
      activeUsers: 54,
      messageCount: 678,
      lastActive: "12m ago",
      trend: "steady",
      gradient: "from-green-400 to-emerald-500",
      icon: <GraduationCap className="w-full h-full" />,
    },
    {
      id: "administrative-processing",
      name: "221g Admin Processing",
      category: "Issues",
      activeUsers: 43,
      messageCount: 567,
      lastActive: "15m ago",
      trend: "rising",
      gradient: "from-yellow-400 to-orange-500",
      icon: <Clock className="w-full h-full" />,
    },
    {
      id: "interview-experience",
      name: "Interview Experiences",
      category: "General",
      activeUsers: 38,
      messageCount: 489,
      lastActive: "18m ago",
      trend: "steady",
      gradient: "from-indigo-400 to-purple-500",
      icon: <MessageSquare className="w-full h-full" />,
    },
    {
      id: "visa-appointment",
      name: "Visa Appointments",
      category: "Scheduling",
      activeUsers: 32,
      messageCount: 401,
      lastActive: "22m ago",
      trend: "steady",
      gradient: "from-pink-400 to-rose-500",
      icon: <Calendar className="w-full h-full" />,
    },
    {
      id: "documents-checklist",
      name: "Documents Checklist",
      category: "Preparation",
      activeUsers: 28,
      messageCount: 356,
      lastActive: "25m ago",
      trend: "steady",
      gradient: "from-cyan-400 to-blue-500",
      icon: <CheckCircle className="w-full h-full" />,
    },
  ]);

  const [hoveredTopic, setHoveredTopic] = useState<string | null>(null);

  // Fetch room statistics from API
  useEffect(() => {
    const fetchRoomStats = async () => {
      try {
        const response = await axios.get('/chat/room-stats');
        if (response.data.success) {
          const statsMap: Record<string, { online_users: number; message_count: number }> = {};
          response.data.rooms.forEach((room: any) => {
            statsMap[room.room_id] = {
              online_users: room.online_users,
              message_count: room.message_count
            };
          });
          setRoomStats(statsMap);
        }
      } catch (error) {
        console.error('Failed to fetch room stats:', error);
      }
    };

    // Fetch immediately
    fetchRoomStats();

    // Refresh every 10 seconds
    const interval = setInterval(fetchRoomStats, 10000);

    return () => clearInterval(interval);
  }, []);

  const getTrendBadge = (trend: string) => {
    switch (trend) {
      case "hot":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 text-xs font-semibold">
            <Zap className="w-3 h-3" />
            Hot
          </span>
        );
      case "rising":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 text-xs font-semibold">
            <TrendingUp className="w-3 h-3" />
            Rising
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 text-xs font-semibold">
            <MessageCircle className="w-3 h-3" />
            Active
          </span>
        );
    }
  };

  return (
    <Box
      sx={{
        minHeight: "100vh",
        background: isDark
          ? "linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)"
          : "linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)",
        py: { xs: 3, sm: 4, md: 6 },
        px: { xs: 2, sm: 3 },
      }}
    >
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-center mb-8"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-gradient-to-r from-blue-500 to-purple-500 text-white mb-3 text-sm md:text-base md:px-4 md:py-2 md:mb-4">
            <Sparkles className="w-3 h-3 md:w-4 md:h-4" />
            <span className="text-xs font-semibold md:text-sm">Trending Discussions</span>
          </div>
          <h1
            className={`text-3xl md:text-4xl lg:text-5xl font-bold mb-2 md:mb-3 ${
              isDark ? "text-white" : "text-gray-900"
            }`}
          >
            Popular Topics
          </h1>
          <p
            className={`text-sm md:text-base lg:text-lg ${
              isDark ? "text-gray-300" : "text-gray-600"
            }`}
          >
            Join thousands of users discussing visa-related topics
          </p>
        </motion.div>

        {/* Stats Bar */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="flex flex-col sm:flex-row justify-center gap-3 sm:gap-6 mb-6 sm:mb-8 md:mb-12"
        >
          <div
            className={`px-4 py-3 sm:px-6 sm:py-4 rounded-xl sm:rounded-2xl ${
              isDark
                ? "bg-white/10 backdrop-blur-lg border border-white/20"
                : "bg-white/80 backdrop-blur-lg border border-gray-200 shadow-lg"
            }`}
          >
            <div className="flex items-center gap-2 sm:gap-3">
              <div
                className={`p-1.5 sm:p-2 rounded-lg ${
                  isDark ? "bg-blue-500/20" : "bg-blue-100"
                }`}
              >
                <Users
                  className={`w-4 h-4 sm:w-5 sm:h-5 ${
                    isDark ? "text-blue-400" : "text-blue-600"
                  }`}
                />
              </div>
              <div>
                <p
                  className={`text-xl sm:text-2xl font-bold ${
                    isDark ? "text-white" : "text-gray-900"
                  }`}
                >
                  {Object.values(roomStats).reduce((sum, room) => sum + room.online_users, 0)}
                </p>
                <p
                  className={`text-xs sm:text-sm ${
                    isDark ? "text-gray-300" : "text-gray-600"
                  }`}
                >
                  Online Now
                </p>
              </div>
            </div>
          </div>
          <div
            className={`px-6 py-4 rounded-2xl ${
              isDark
                ? "bg-white/10 backdrop-blur-lg border border-white/20"
                : "bg-white/80 backdrop-blur-lg border border-gray-200 shadow-lg"
            }`}
          >
            <div className="flex items-center gap-3">
              <div
                className={`p-2 rounded-lg ${
                  isDark ? "bg-purple-500/20" : "bg-purple-100"
                }`}
              >
                <MessageCircle
                  className={`w-5 h-5 ${
                    isDark ? "text-purple-400" : "text-purple-600"
                  }`}
                />
              </div>
              <div>
                <p
                  className={`text-2xl font-bold ${
                    isDark ? "text-white" : "text-gray-900"
                  }`}
                >
                  {topics.length}
                </p>
                <p
                  className={`text-sm ${
                    isDark ? "text-gray-300" : "text-gray-600"
                  }`}
                >
                  Active Topics
                </p>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Topics Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 sm:gap-5 md:gap-6">
          {topics.map((topic, index) => (
            <motion.div
              key={topic.id}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{
                delay: index * 0.1,
                duration: 0.3,
              }}
              whileHover={{ scale: 1.05, y: -5 }}
              onClick={() => onTopicSelect(topic.id, topic.name)}
              onMouseEnter={() => setHoveredTopic(topic.id)}
              onMouseLeave={() => setHoveredTopic(null)}
              className={`cursor-pointer rounded-xl sm:rounded-2xl p-4 sm:p-5 md:p-6 transition-all duration-300 ${
                isDark
                  ? "bg-white/10 backdrop-blur-lg border border-white/20 hover:bg-white/20"
                  : "bg-white border border-gray-200 hover:shadow-2xl shadow-lg"
              }`}
            >
              {/* Topic Header */}
              <div className="flex items-start justify-between mb-3 sm:mb-4">
                <div
                  className={`w-12 h-12 sm:w-14 sm:h-14 flex items-center justify-center rounded-lg sm:rounded-xl transition-all duration-300 ${
                    isDark 
                      ? "bg-gradient-to-br from-white/20 to-white/10 text-white shadow-lg" 
                      : "bg-gradient-to-br from-gray-100 to-gray-50 text-gray-800 shadow-md"
                  } ${
                    hoveredTopic === topic.id
                      ? isDark
                        ? "from-blue-500/30 to-purple-500/30"
                        : "from-blue-50 to-purple-50"
                      : ""
                  }`}
                >
                  <div className="w-6 h-6 sm:w-7 sm:h-7">
                    {topic.icon}
                  </div>
                </div>
                {getTrendBadge(topic.trend)}
              </div>

              {/* Topic Title */}
              <h3
                className={`text-base sm:text-lg font-bold mb-1 sm:mb-2 ${
                  isDark ? "text-white" : "text-gray-900"
                }`}
              >
                {topic.name}
              </h3>

              {/* Category */}
              <p
                className={`text-xs sm:text-sm mb-3 sm:mb-4 ${
                  isDark ? "text-gray-400" : "text-gray-600"
                }`}
              >
                {topic.category}
              </p>

              {/* Stats */}
              <div className="space-y-1.5 sm:space-y-2 mb-3 sm:mb-4">
                <div className="flex items-center justify-between">
                  <span
                    className={`text-xs sm:text-sm flex items-center gap-1.5 sm:gap-2 ${
                      isDark ? "text-gray-300" : "text-gray-600"
                    }`}
                  >
                    <Users className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                    {roomStats[topic.id]?.online_users ?? 0} online
                  </span>
                  <span
                    className={`text-xs sm:text-sm flex items-center gap-1.5 sm:gap-2 ${
                      isDark ? "text-gray-300" : "text-gray-600"
                    }`}
                  >
                    <MessageCircle className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                    {roomStats[topic.id]?.message_count ?? 0}
                  </span>
                </div>
                <p
                  className={`text-xs ${
                    isDark ? "text-gray-400" : "text-gray-500"
                  }`}
                >
                  Active {topic.lastActive}
                </p>
              </div>

              {/* Action Button */}
              <div
                className={`flex items-center justify-between pt-3 sm:pt-4 border-t ${
                  isDark ? "border-white/10" : "border-gray-200"
                }`}
              >
                <span
                  className={`text-xs sm:text-sm font-semibold ${
                    isDark ? "text-blue-400" : "text-blue-600"
                  }`}
                >
                  Join Discussion
                </span>
                <ArrowRight
                  className={`w-4 h-4 sm:w-5 sm:h-5 transition-transform ${
                    hoveredTopic === topic.id ? "translate-x-1" : ""
                  } ${isDark ? "text-blue-400" : "text-blue-600"}`}
                />
              </div>
            </motion.div>
          ))}
        </div>

        {/* Footer Tip */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
          className="text-center mt-8 sm:mt-10 md:mt-12"
        >
          <div className="inline-flex items-center gap-2">
            <div className={`w-4 h-4 sm:w-5 sm:h-5 ${isDark ? "text-yellow-400" : "text-yellow-500"}`}>
              <Sparkles className="w-full h-full" />
            </div>
            <p
              className={`text-xs sm:text-sm ${isDark ? "text-gray-400" : "text-gray-600"}`}
            >
              Click on any topic card to join the conversation
            </p>
          </div>
        </motion.div>
      </div>
    </Box>
  );
};

export default TopicsHome;
