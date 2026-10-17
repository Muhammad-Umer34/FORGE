// D:\FYP\FORGE-1\frontend\src\components\chat\ChatInput.tsx
"use client";

import React, { useState, useRef, useEffect } from "react";
import { ArrowUp, Loader2 } from "lucide-react";

interface ChatInputProps {
  onSendMessage: (text: string) => void;
  isLoading: boolean;
  placeholder?: string;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  isLoading,
  placeholder = "Describe what you want to build...",
}) => {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        180
      )}px`;
    }
  }, [input]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;

    onSendMessage(trimmed);
    setInput("");

    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="border-t border-zinc-850 bg-zinc-950/90 backdrop-blur-md px-4 py-3 sm:py-4 sticky bottom-0 z-20">
      <div className="max-w-3xl mx-auto">
        <form
          onSubmit={handleSubmit}
          className="relative flex items-end gap-2 bg-zinc-900/90 border border-zinc-800/80 focus-within:border-zinc-700 focus-within:ring-1 focus-within:ring-zinc-700 rounded-2xl p-2.5 transition-all duration-200 shadow-lg shadow-black/50"
        >
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            rows={1}
            placeholder={placeholder}
            className="flex-1 max-h-44 resize-none bg-transparent px-3 py-1.5 text-sm sm:text-base text-zinc-100 placeholder-zinc-500 focus:outline-none disabled:opacity-50"
          />

          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="flex-shrink-0 w-8 h-8 rounded-xl bg-white hover:bg-zinc-200 disabled:bg-zinc-800 disabled:text-zinc-600 text-black flex items-center justify-center transition-all duration-150 active:scale-95 cursor-pointer disabled:cursor-not-allowed shadow"
            title="Send message (Enter)"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin text-zinc-400" />
            ) : (
              <ArrowUp className="w-4 h-4 stroke-[2.5]" />
            )}
          </button>
        </form>

        <div className="flex items-center justify-center mt-2 px-1 text-[11px] text-zinc-500">
          <span>Enter to send • Shift + Enter for new line</span>
        </div>
      </div>
    </div>
  );
};
