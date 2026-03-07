"use client";

import { useState } from "react";
import type { Step } from "@/types/chat";

type ThinkingPanelProps = {
  steps:       Step[];
  isStreaming: boolean;
};

export function ThinkingPanel({ steps, isStreaming }: ThinkingPanelProps) {
  const [open, setOpen] = useState(true);

  if (steps.length === 0) return null;

  const allDone = steps.every((s) => s.done);

  return (
    <div className="mb-4 rounded-xl border border-gray-200 bg-gray-50 text-sm overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-4 py-2.5 text-gray-500 hover:text-gray-700 transition-colors"
      >
        <span className="flex items-center gap-2 font-medium">
          {isStreaming && !allDone ? (
            <span className="inline-flex gap-0.5">
              <span className="w-1 h-1 rounded-full bg-gray-400 animate-bounce [animation-delay:0ms]" />
              <span className="w-1 h-1 rounded-full bg-gray-400 animate-bounce [animation-delay:150ms]" />
              <span className="w-1 h-1 rounded-full bg-gray-400 animate-bounce [animation-delay:300ms]" />
            </span>
          ) : (
            <span>&#10003;</span>
          )}
          思考过程
        </span>
        <span className="text-xs text-gray-400">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="border-t border-gray-200 divide-y divide-gray-100">
          {steps.map((step, i) => (
            <div key={i} className="px-4 py-3 flex flex-col gap-1">
              <div className="flex items-center gap-2 text-gray-600">
                {step.done ? (
                  <span className="text-green-500">&#10003;</span>
                ) : (
                  <span className="inline-block w-3 h-3 rounded-full border-2 border-gray-400 border-t-transparent animate-spin" />
                )}
                <span className="flex items-center gap-1.5">
                  <svg viewBox="0 0 24 24" fill="none" className="w-3.5 h-3.5 shrink-0 text-gray-400" stroke="currentColor" strokeWidth="2">
                    <path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/>
                  </svg>
                  <span className="font-medium text-gray-700">{step.tool}</span>
                  <span className="text-gray-400">：</span>
                  <span className="text-gray-600">{step.query}</span>
                </span>
              </div>
              {step.snippet && (
                <p className="ml-6 text-xs text-gray-400 line-clamp-2">{step.snippet}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
