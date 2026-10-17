// D:\FYP\FORGE-1\frontend\src\components\chat\EmptyState.tsx
"use client";

import React from "react";
import { Sparkles } from "lucide-react";

export const EmptyState: React.FC = () => {
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 text-center max-w-md mx-auto my-auto animate-fade-in">
      <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-violet-600 via-indigo-600 to-pink-500 flex items-center justify-center shadow-lg shadow-violet-500/20 mb-4">
        <Sparkles className="w-6 h-6 text-white" />
      </div>

      <h2 className="text-xl sm:text-2xl font-semibold text-white tracking-tight mb-2">
        What do you want to build?
      </h2>
      <p className="text-sm text-zinc-400 leading-relaxed max-w-sm">
        Describe your website idea, business requirements, or design preferences to get started.
      </p>
    </div>
  );
};
