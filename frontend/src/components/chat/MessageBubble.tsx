import { User, Bot, Loader2 } from "lucide-react";
import { Message } from "../../types/chat";
import ReactMarkdown from "react-markdown";

interface MessageBubbleProps {
  message: Message;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary-600 flex items-center justify-center">
          <Bot className="w-5 h-5 text-white" />
        </div>
      )}

      <div
        className={`max-w-3xl ${
          isUser
            ? "bg-primary-600 text-white"
            : "bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
        } rounded-2xl px-4 py-3 shadow-sm`}
      >
        {message.isStreaming ? (
          <div className="flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm">Thinking...</span>
          </div>
        ) : (
          <>
            <div className="prose prose-sm max-w-none dark:prose-invert">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>

            {/* Show sources if available */}
            {message.sources && message.sources.length > 0 && (
              <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                <details className="text-xs">
                  <summary className="cursor-pointer font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200">
                    View {message.sources.length} sources
                  </summary>
                  <div className="mt-2 space-y-2">
                    {message.sources.slice(0, 3).map((source: any, idx) => {
                      // Check if this is a RedBus2US source (has title/url) or a conversation source (has metadata)
                      const isRedBusSource = source.title && source.url;

                      return (
                        <div
                          key={source.id || idx}
                          className="p-2 bg-gray-50 dark:bg-gray-700/50 rounded text-gray-700 dark:text-gray-300"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex-1">
                              {isRedBusSource ? (
                                // RedBus2US source
                                <>
                                  <a
                                    href={source.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="font-medium mb-1 text-primary-600 dark:text-primary-400 hover:underline"
                                  >
                                    {source.title}
                                  </a>
                                  <div className="text-gray-500 dark:text-gray-400 text-xs mt-1">
                                    {source.date} •{" "}
                                    {(
                                      (source.relevance_score || 0) * 100
                                    ).toFixed(0)}
                                    % relevance
                                  </div>
                                </>
                              ) : (
                                // Conversation source
                                <>
                                  <div className="font-medium mb-1">
                                    Source {idx + 1} (
                                    {((source.score || 0) * 100).toFixed(0)}%
                                    match)
                                  </div>
                                  <div className="text-gray-600 dark:text-gray-400 line-clamp-2">
                                    {source.text}
                                  </div>
                                  {source.metadata && (
                                    <div className="mt-1 flex gap-2 text-xs">
                                      {source.metadata.visa_type && (
                                        <span className="badge badge-info">
                                          {source.metadata.visa_type}
                                        </span>
                                      )}
                                      {source.metadata.primary_category && (
                                        <span className="badge bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-300">
                                          {source.metadata.primary_category.replace(
                                            /_/g,
                                            " "
                                          )}
                                        </span>
                                      )}
                                    </div>
                                  )}
                                </>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </details>
              </div>
            )}
          </>
        )}

        <div
          className={`text-xs mt-2 ${
            isUser ? "text-blue-100" : "text-gray-400"
          }`}
        >
          {message.timestamp.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </div>
      </div>

      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center">
          <User className="w-5 h-5 text-white" />
        </div>
      )}
    </div>
  );
}
