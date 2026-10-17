// D:\FYP\FORGE-1\frontend\src\components\chat\ForgeChatbot.tsx
"use client";

import React, { useState, useEffect, useRef } from "react";
import { ChatMessage } from "@/types/chat";
import { sendChatMessage, resetChatSession, checkBackendHealth } from "@/services/api";
import { ChatHeader } from "./ChatHeader";
import { EmptyState } from "./EmptyState";
import { ChatMessageItem } from "./ChatMessageItem";
import { ChatInput } from "./ChatInput";
import { Sparkles, Loader2, AlertCircle } from "lucide-react";

export default function ForgeChatbot() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isResetting, setIsResetting] = useState<boolean>(false);
  const [isBackendHealthy, setIsBackendHealthy] = useState<boolean | null>(null);
  const [turnCount, setTurnCount] = useState<number>(0);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initialize or restore session from localStorage
  useEffect(() => {
    const savedSessionId = localStorage.getItem("forge_session_id");
    const activeSession = savedSessionId || `forge_${Math.random().toString(36).substring(2, 10)}`;
    setSessionId(activeSession);
    if (!savedSessionId) {
      localStorage.setItem("forge_session_id", activeSession);
    }

    const savedMessages = localStorage.getItem(`forge_messages_${activeSession}`);
    if (savedMessages) {
      try {
        const parsed = JSON.parse(savedMessages);
        setMessages(parsed);
        setTurnCount(Math.floor(parsed.length / 2));
      } catch {
        // Ignore parse error
      }
    }

    // Check backend health
    checkBackendHealth().then((healthy) => {
      setIsBackendHealthy(healthy);
      if (!healthy) {
        setErrorBanner("Backend at http://localhost:8000 is not reachable. Make sure the backend server is running.");
      }
    });

    const interval = setInterval(() => {
      checkBackendHealth().then((healthy) => {
        setIsBackendHealthy(healthy);
        if (healthy) setErrorBanner(null);
      });
    }, 15000);

    return () => clearInterval(interval);
  }, []);

  // Save messages to localStorage when updated
  useEffect(() => {
    if (sessionId && messages.length > 0) {
      localStorage.setItem(`forge_messages_${sessionId}`, JSON.stringify(messages));
    }
  }, [messages, sessionId]);

  // Scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Handle sending a message
  const handleSendMessage = async (text: string) => {
    if (!text.trim() || isLoading) return;

    setErrorBanner(null);

    const userMsg: ChatMessage = {
      id: `msg_${Date.now()}_user`,
      sender: "user",
      text: text.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const response = await sendChatMessage(text.trim(), sessionId);

      const botMsg: ChatMessage = {
        id: `msg_${Date.now()}_forge`,
        sender: "forge",
        text: response.reply,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        intent: response.intent,
        turnCount: response.turn_count,
      };

      setMessages((prev) => [...prev, botMsg]);
      setTurnCount(response.turn_count);
      setIsBackendHealthy(true);
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error
          ? err.message
          : "Could not reach FORGE backend. Please ensure the FastAPI server is running on http://localhost:8000.";

      const botErrorMsg: ChatMessage = {
        id: `msg_${Date.now()}_forge_err`,
        sender: "forge",
        text: `Error: ${errorMessage}`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        isError: true,
      };

      setMessages((prev) => [...prev, botErrorMsg]);
      setErrorBanner(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle resetting session memory
  const handleResetSession = async () => {
    if (isResetting) return;
    setIsResetting(true);

    try {
      if (sessionId) {
        await resetChatSession(sessionId);
        localStorage.removeItem(`forge_messages_${sessionId}`);
      }
      const newSession = `forge_${Math.random().toString(36).substring(2, 10)}`;
      setSessionId(newSession);
      localStorage.setItem("forge_session_id", newSession);
      setMessages([]);
      setTurnCount(0);
      setErrorBanner(null);
    } catch {
      // Local fallback reset
      const newSession = `forge_${Math.random().toString(36).substring(2, 10)}`;
      setSessionId(newSession);
      localStorage.setItem("forge_session_id", newSession);
      setMessages([]);
      setTurnCount(0);
    } finally {
      setIsResetting(false);
    }
  };

  return (
    <div className="flex flex-col h-screen w-full bg-zinc-950 text-zinc-100 overflow-hidden font-sans">
      {/* Top Header */}
      <ChatHeader
        isBackendHealthy={isBackendHealthy}
        onResetSession={handleResetSession}
        isResetting={isResetting}
      />

      {/* Optional Error/Warning Banner */}
      {errorBanner && (
        <div className="bg-amber-950/70 border-b border-amber-800/60 px-4 py-2 text-xs text-amber-200 flex items-center justify-between z-10">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0" />
            <span>{errorBanner}</span>
          </div>
          <button
            onClick={() => setErrorBanner(null)}
            className="text-amber-400 hover:text-white ml-2 text-xs cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main Chat Scroll Area */}
      <main className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 max-w-4xl w-full mx-auto flex flex-col">
        {messages.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="flex-1 flex flex-col justify-start">
            {messages.map((msg) => (
              <ChatMessageItem key={msg.id} message={msg} />
            ))}

            {/* Loading / Thinking Indicator */}
            {isLoading && (
              <div className="flex gap-3 sm:gap-4 my-4 w-full justify-start animate-fade-in">
                <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-violet-600 via-indigo-600 to-pink-500 flex items-center justify-center text-white shadow-md shadow-violet-500/20 mt-1">
                  <Sparkles className="w-4 h-4 animate-spin" />
                </div>
                <div className="bg-zinc-900/90 border border-zinc-800/80 rounded-2xl rounded-tl-xs px-4 py-3 text-sm text-zinc-400 flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-violet-400" />
                  <span>FORGE is thinking...</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </main>

      {/* Sticky Bottom Input */}
      <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
    </div>
  );
}
