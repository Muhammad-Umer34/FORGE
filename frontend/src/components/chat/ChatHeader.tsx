// D:\FYP\FORGE-1\frontend\src\components\chat\ChatHeader.tsx
"use client";

import React from "react";
import { Sparkles, SquarePen } from "lucide-react";

interface ChatHeaderProps {
  isBackendHealthy: boolean | null;
  onResetSession: () => void;
  isResetting: boolean;
}

export const ChatHeader: React.FC<ChatHeaderProps> = ({
  isBackendHealthy,
  onResetSession,
  isResetting,
}) => {
  return (
    <header className="border-b border-zinc-800/80 bg-zinc-950/90 backdrop-blur-md px-4 sm:px-6 py-3 flex items-center justify-between sticky top-0 z-20">
      {/* Brand & Identity */}
      <div className="flex items-center gap-3">
        <div className="relative flex items-center justify-center w-9 h-9 rounded-xl bg-gradient-to-tr from-violet-600 via-indigo-600 to-pink-500 shadow-md shadow-violet-500/20">
          <Sparkles className="w-4 h-4 text-white" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-base font-bold tracking-tight text-white">
              FORGE
            </h1>
            <span className="text-[11px] px-2 py-0.5 rounded-full font-medium bg-zinc-800 text-zinc-300 border border-zinc-700/60">
              Studio
            </span>
          </div>
          <p className="text-xs text-zinc-400 hidden sm:block">
            AI Website Builder
          </p>
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-3">
        {/* Subtle Online Status Dot */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-zinc-900 border border-zinc-800 text-xs">
          <span
            className={`w-2 h-2 rounded-full ${
              isBackendHealthy === true
                ? "bg-emerald-400 shadow-sm shadow-emerald-400/50"
                : isBackendHealthy === false
                ? "bg-amber-400"
                : "bg-zinc-500"
            }`}
          />
          <span className="text-zinc-400 text-[11px]">
            {isBackendHealthy === true
              ? "Online"
              : isBackendHealthy === false
              ? "Connecting"
              : "Checking"}
          </span>
        </div>

        {/* New Chat Button */}
        <button
          onClick={onResetSession}
          disabled={isResetting}
          title="Start a new chat session"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-zinc-200 hover:text-white bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 hover:border-zinc-700 transition-all duration-150 active:scale-95 disabled:opacity-50 cursor-pointer"
        >
          <SquarePen className={`w-3.5 h-3.5 ${isResetting ? "animate-spin text-violet-400" : ""}`} />
          <span>New Chat</span>
        </button>
      </div>
    </header>
  );
};
