import { useRef, useEffect } from "react";
import { Menu } from "lucide-react";
import MessageBubble from "./MessageBubble";
import ChatInput from "./ChatInput";
import Welcome from "./Welcome";
import { Conversation } from "../../types/chat";

interface ChatAreaProps {
  conversation: Conversation | undefined;
  onSendMessage: (content: string) => void;
  isLoading: boolean;
  onToggleSidebar?: () => void;
  hideSidebarToggle?: boolean;
}

export default function ChatArea({
  conversation,
  onSendMessage,
  isLoading,
  onToggleSidebar,
  hideSidebarToggle = false,
}: ChatAreaProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [conversation?.messages]);

  return (
    <div className="flex-1 flex flex-col h-full">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 py-3 flex items-center gap-3">
        {!hideSidebarToggle && onToggleSidebar && (
          <button
            onClick={onToggleSidebar}
            className="lg:hidden p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
            Visa Assistant
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Ask me anything about visa processes
          </p>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {!conversation || conversation.messages.length === 0 ? (
          <Welcome onSendMessage={onSendMessage} />
        ) : (
          <>
            {conversation.messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                isUser={message.role === "user"}
              />
            ))}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input Area */}
      <ChatInput onSendMessage={onSendMessage} isLoading={isLoading} />
    </div>
  );
}
