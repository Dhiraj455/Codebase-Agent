"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Array<{
    file: string;
    chunk_type: string;
    name: string;
    score: number;
    preview: string;
  }>;
  timestamp?: Date;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  useEffect(() => {
    const analysisId = sessionStorage.getItem("analysis_id");
    if (!analysisId) {
      router.push("/");
      return;
    }

    // Focus input on mount
    inputRef.current?.focus();
  }, [router]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setError("");
    setLoading(true);

    try {
      const analysisId = sessionStorage.getItem("analysis_id");
      const repoName = sessionStorage.getItem("repo_name");

      const response = await fetch("/api/proxy/ask", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: userMessage.content,
          analysis_id: analysisId,
          repo_name: repoName,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to get answer");
      }

      const data = await response.json();

      const assistantMessage: Message = {
        role: "assistant",
        content: data.answer || "I couldn't generate an answer. Please try again.",
        sources: data.sources || [],
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      const errorMessage: Message = {
        role: "assistant",
        content: err instanceof Error ? err.message : "Sorry, I couldn't process your question. Please try again.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
      // Refocus input after response
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const clearChat = () => {
    setMessages([]);
    setError("");
    inputRef.current?.focus();
  };

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-900 flex flex-col">
      {/* Header */}
      <div className="bg-white dark:bg-zinc-800 border-b border-zinc-200 dark:border-zinc-700 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div>
            <Link
              href="/analysis"
              className="text-blue-600 hover:underline mb-2 inline-block text-sm"
            >
              ← Back to Analysis
            </Link>
            <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
              Ask Questions
            </h1>
            <p className="text-sm text-zinc-600 dark:text-zinc-400 mt-1">
              Ask questions about the codebase using AI-powered analysis
            </p>
          </div>
          {messages.length > 0 && (
            <button
              onClick={clearChat}
              className="px-3 py-1.5 text-sm rounded-lg border border-zinc-300 dark:border-zinc-700 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-700 transition-colors"
            >
              Clear Chat
            </button>
          )}
        </div>
      </div>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-6 py-6">
          {messages.length === 0 && (
            <div className="text-center py-12">
              <div className="max-w-md mx-auto space-y-4">
                <div className="text-4xl mb-4">💬</div>
                <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">
                  Start a Conversation
                </h2>
                <p className="text-zinc-600 dark:text-zinc-400">
                  Ask questions about the codebase architecture, code smells, refactoring strategies, or any specific files or functions.
                </p>
                <div className="mt-6 space-y-2 text-sm text-zinc-500 dark:text-zinc-500">
                  <p className="font-medium">Example questions:</p>
                  <ul className="list-disc list-inside space-y-1 text-left max-w-xs mx-auto">
                    <li>"What is the overall architecture?"</li>
                    <li>"How does authentication work?"</li>
                    <li>"What are the main code smells?"</li>
                    <li>"Explain the dependency structure"</li>
                  </ul>
                </div>
              </div>
            </div>
          )}

          <div className="space-y-4">
            {messages.map((message, index) => (
              <div
                key={index}
                className={`flex ${
                  message.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                <div
                  className={`max-w-[85%] md:max-w-[75%] rounded-lg p-4 ${
                    message.role === "user"
                      ? "bg-blue-600 text-white"
                      : "bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-50 border border-zinc-200 dark:border-zinc-700"
                  }`}
                >
                  <div className="flex items-start gap-2 mb-1">
                    <span className="text-xs font-medium opacity-70">
                      {message.role === "user" ? "You" : "AI Assistant"}
                    </span>
                    {message.timestamp && (
                      <span className="text-xs opacity-60">
                        {message.timestamp.toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                    )}
                  </div>
                  <p className="whitespace-pre-wrap break-words">{message.content}</p>
                  
                  {message.sources && message.sources.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-zinc-200 dark:border-zinc-700">
                      <p className="text-xs font-semibold mb-2 opacity-80">
                        Sources ({message.sources.length}):
                      </p>
                      <div className="space-y-2">
                        {message.sources.map((source, idx) => (
                          <div
                            key={idx}
                            className="text-xs p-2 rounded bg-zinc-100 dark:bg-zinc-700/50"
                          >
                            <div className="flex items-center gap-2 mb-1">
                              <span className="font-medium">{source.file}</span>
                              <span className="px-1.5 py-0.5 rounded bg-zinc-200 dark:bg-zinc-600 text-[10px]">
                                {source.chunk_type}
                              </span>
                              {source.score && (
                                <span className="text-[10px] opacity-70">
                                  ({(source.score * 100).toFixed(1)}% match)
                                </span>
                              )}
                            </div>
                            {source.preview && (
                              <p className="opacity-70 line-clamp-2 text-[10px] mt-1">
                                {source.preview}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex justify-start">
                <div className="bg-white dark:bg-zinc-800 rounded-lg p-4 border border-zinc-200 dark:border-zinc-700">
                  <div className="flex items-center gap-2">
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-zinc-400 rounded-full animate-bounce"></div>
                      <div
                        className="w-2 h-2 bg-zinc-400 rounded-full animate-bounce"
                        style={{ animationDelay: "0.2s" }}
                      ></div>
                      <div
                        className="w-2 h-2 bg-zinc-400 rounded-full animate-bounce"
                        style={{ animationDelay: "0.4s" }}
                      ></div>
                    </div>
                    <span className="text-sm text-zinc-600 dark:text-zinc-400 ml-2">
                      Thinking...
                    </span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="max-w-4xl mx-auto px-6 pb-2">
          <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className="bg-white dark:bg-zinc-800 border-t border-zinc-200 dark:border-zinc-700 px-6 py-4">
        <div className="max-w-4xl mx-auto">
          <form onSubmit={handleSubmit} className="flex gap-3">
            <div className="flex-1 relative">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a question about the codebase..."
                className="w-full px-4 py-3 pr-12 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-50 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={loading}
              />
              <div className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-zinc-400">
                Press Enter to send
              </div>
            </div>
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="px-6 py-3 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:bg-zinc-400 disabled:cursor-not-allowed text-white font-medium transition-colors flex items-center gap-2 min-w-[100px] justify-center"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  <span>Sending...</span>
                </>
              ) : (
                <span>Send</span>
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
