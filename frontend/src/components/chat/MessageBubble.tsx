import React from "react";
import { Message } from "../../types/chat";

interface Source {
  type: "redbus2us" | "community";
  url?: string;
  title?: string;
  relevance?: number;
  category?: string;
  visa_type?: string;
  published_date?: string;
  article_type?: string;
  text?: string;
}

interface MessageBubbleProps {
  message: Message;
  isUser: boolean;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message, isUser }) => {
  // Helper function to format date
  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
    } catch (e) {
      return dateStr;
    }
  };

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div
        className={`max-w-[65%] rounded-lg px-4 py-2 ${
          isUser
            ? "bg-blue-500 text-white"
            : "bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100"
        }`}
      >
        {/* Message Text */}
        <div className="text-sm whitespace-pre-wrap">{message.text}</div>

        {/* Sources Section */}
        {message.sources && message.sources.length > 0 && (
          <div className="mt-3 border-t border-gray-200 dark:border-gray-700 pt-2">
            <div className="text-xs font-medium mb-1 text-gray-500 dark:text-gray-400">
              Sources:
            </div>
            <div className="space-y-2">
              {message.sources.map((source: Source, index: number) => (
                <div
                  key={index}
                  className={`text-xs p-2 rounded ${
                    source.type === "redbus2us"
                      ? "bg-green-50 dark:bg-green-900/20"
                      : "bg-blue-50 dark:bg-blue-900/20"
                  }`}
                >
                  {/* RedBus2US Source */}
                  {source.type === "redbus2us" && (
                    <>
                      <div className="flex items-center justify-between">
                        <a
                          href={source.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-medium text-green-600 dark:text-green-400 hover:underline"
                        >
                          {source.title}
                        </a>
                        <span className="text-green-500 dark:text-green-400">
                          {source.relevance}% match
                        </span>
                      </div>
                      <div className="mt-1 text-gray-500 dark:text-gray-400 flex items-center justify-between">
                        <span>
                          {source.published_date &&
                            formatDate(source.published_date)}
                        </span>
                        <span className="px-2 py-0.5 rounded bg-green-100 dark:bg-green-800 text-green-700 dark:text-green-300">
                          {source.article_type}
                        </span>
                      </div>
                    </>
                  )}

                  {/* Community Source */}
                  {source.type === "community" && (
                    <>
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-blue-600 dark:text-blue-400">
                          Community Experience
                        </span>
                        <span className="text-blue-500 dark:text-blue-400">
                          {source.relevance}% match
                        </span>
                      </div>
                      <div className="mt-1 text-gray-600 dark:text-gray-300">
                        {source.text &&
                          (source.text.length > 150
                            ? `${source.text.substring(0, 150)}...`
                            : source.text)}
                      </div>
                      <div className="mt-1 text-gray-500 dark:text-gray-400 flex items-center justify-between">
                        <span>{source.visa_type}</span>
                        <span className="px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-800 text-blue-700 dark:text-blue-300">
                          {source.category}
                        </span>
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageBubble;
