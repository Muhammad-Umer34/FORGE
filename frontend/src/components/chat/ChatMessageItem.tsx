// D:\FYP\FORGE-1\frontend\src\components\chat\ChatMessageItem.tsx
"use client";

import React, { useState } from "react";
import { ChatMessage } from "@/types/chat";
import { Sparkles, User, Copy, Check } from "lucide-react";

interface ChatMessageItemProps {
  message: ChatMessage;
}

export const ChatMessageItem: React.FC<ChatMessageItemProps> = ({ message }) => {
  const isUser = message.sender === "user";
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  const renderFormattedText = (rawText: string) => {
    const lines = rawText.split("\n");

    return lines.map((line, lineIndex) => {
      const isBullet = line.trim().startsWith("- ") || line.trim().startsWith("* ");
      const isNumbered = /^\d+\.\s/.test(line.trim());

      let cleanLine = line;
      if (isBullet) {
        cleanLine = line.trim().replace(/^[-*]\s+/, "");
      } else if (isNumbered) {
        cleanLine = line.trim().replace(/^\d+\.\s+/, "");
      }

      const parts = cleanLine.split(/(\*\*.*?\*\*)/g);
      const parsedContent = parts.map((part, partIndex) => {
        if (part.startsWith("**") && part.endsWith("**")) {
          return (
            <strong key={partIndex} className="font-semibold text-white">
              {part.slice(2, -2)}
            </strong>
          );
        }
        return part;
      });

      if (isBullet) {
        return (
          <li key={lineIndex} className="ml-4 list-disc text-zinc-300 my-1">
            {parsedContent}
          </li>
        );
      }

      if (isNumbered) {
        const numMatch = line.trim().match(/^(\d+)\./);
        const num = numMatch ? numMatch[1] : "•";
        return (
          <div key={lineIndex} className="flex gap-2.5 my-1.5 items-start">
            <span className="font-mono text-xs px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-300 font-medium">
              {num}
            </span>
            <div className="text-zinc-200">{parsedContent}</div>
          </div>
        );
      }

      if (line.trim() === "") {
        return <div key={lineIndex} className="h-2" />;
      }

      return (
        <p key={lineIndex} className="my-1 leading-relaxed">
          {parsedContent}
        </p>
      );
    });
  };

  return (
    <div
      className={`flex gap-3 sm:gap-4 my-4 w-full ${
        isUser ? "justify-end" : "justify-start"
      }`}
    >
      {/* Bot Avatar */}
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-xl bg-gradient-to-tr from-violet-600 via-indigo-600 to-pink-500 flex items-center justify-center text-white shadow-sm mt-0.5">
          <Sparkles className="w-4 h-4" />
        </div>
      )}

      {/* Message Content Container */}
      <div
        className={`relative group max-w-[85%] sm:max-w-[78%] rounded-2xl px-4 sm:px-5 py-3 text-sm sm:text-base leading-relaxed ${
          isUser
            ? "bg-zinc-800 text-white rounded-tr-sm shadow-sm"
            : message.isError
            ? "bg-rose-950/40 text-rose-200 border border-rose-800/50 rounded-tl-sm"
            : "bg-zinc-900/90 text-zinc-200 border border-zinc-800/80 rounded-tl-sm shadow-sm shadow-black/20"
        }`}
      >
        {/* Header line for FORGE responses with subtle copy button */}
        {!isUser && (
          <div className="flex items-center justify-between gap-2 mb-1.5 pb-1 border-b border-zinc-800/50 text-xs">
            <span className="font-semibold text-zinc-300">FORGE</span>

            <button
              onClick={handleCopy}
              title="Copy message"
              className="text-zinc-500 hover:text-zinc-300 p-1 rounded transition-colors opacity-0 group-hover:opacity-100 cursor-pointer"
            >
              {copied ? (
                <Check className="w-3.5 h-3.5 text-emerald-400" />
              ) : (
                <Copy className="w-3.5 h-3.5" />
              )}
            </button>
          </div>
        )}

        {/* Formatted Text Body */}
        <div className="text-zinc-100 space-y-0.5">
          {renderFormattedText(message.text)}
        </div>

        {/* Timestamp */}
        <div
          className={`text-[10px] mt-2 flex items-center gap-1 ${
            isUser ? "text-zinc-400 justify-end" : "text-zinc-500 justify-start"
          }`}
        >
          <span>{message.timestamp}</span>
        </div>
      </div>

      {/* User Avatar */}
      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-xl bg-zinc-800 border border-zinc-700 flex items-center justify-center text-zinc-300 shadow-sm mt-0.5">
          <User className="w-4 h-4" />
        </div>
      )}
    </div>
  );
};
