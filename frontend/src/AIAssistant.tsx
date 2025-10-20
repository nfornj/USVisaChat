import { useState } from "react";
import ChatArea from "./components/chat/ChatArea";
import { Message, Conversation } from "./types/chat";
import { searchAPI } from "./utils/api";

export default function AIAssistant() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async (content: string) => {
    if (!content.trim()) return;

    // Add user message
    const userMessage: Message = {
      id: `msg-${Date.now()}`,
      role: "user",
      content,
      text: content,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);

    // Add streaming placeholder
    const streamingMessage: Message = {
      id: `msg-${Date.now()}-assistant`,
      role: "assistant",
      content: "",
      text: "",
      timestamp: new Date(),
      isStreaming: true,
    };

    setMessages((prev) => [...prev, streamingMessage]);
    setIsLoading(true);

    try {
      // Use new AI endpoint with RedBus2US knowledge
      const aiResponse = await searchAPI.askAI({
        query: content,
        limit: 3, // Top 3 relevant articles
      });

      // Get answer from backend
      let responseText = aiResponse.answer;

      // Add source references (RedBus2US articles)
      if (aiResponse.sources && aiResponse.sources.length > 0) {
        responseText += `\n\n---\n\n**📚 Sources from RedBus2US**:\n\n`;
        aiResponse.sources.forEach((source: any, idx: number) => {
          const relevance = (source.relevance_score * 100).toFixed(0);
          responseText += `${idx + 1}. [**${source.title}**](${source.url})\n`;
          responseText += `   ${source.date} • ${relevance}% relevance\n\n`;
        });

        responseText += `\n*Found ${aiResponse.articles_found} relevant articles • ${aiResponse.confidence}% confidence • ${aiResponse.processing_time_ms}ms*`;
      }

      // Update with actual response
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === streamingMessage.id
            ? {
                ...msg,
                content: responseText,
                isStreaming: false,
                sources: aiResponse.sources,
              }
            : msg
        )
      );
    } catch (error: any) {
      // Handle error
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === streamingMessage.id
            ? {
                ...msg,
                content: `Sorry, I encountered an error: ${
                  error.message || "Failed to search"
                }. Please try again.`,
                isStreaming: false,
              }
            : msg
        )
      );
    } finally {
      setIsLoading(false);
    }
  };

  // Create a simple conversation object for ChatArea
  const currentConversation: Conversation | undefined =
    messages.length > 0
      ? {
          id: "current",
          title: "AI Assistant",
          messages,
          createdAt: new Date(),
          updatedAt: new Date(),
        }
      : undefined;

  return (
    <div className="flex h-full bg-gray-50 dark:bg-gray-900">
      {/* Main Chat Area - Full Width */}
      <ChatArea
        conversation={currentConversation}
        onSendMessage={sendMessage}
        isLoading={isLoading}
        hideSidebarToggle={true}
      />
    </div>
  );
}
