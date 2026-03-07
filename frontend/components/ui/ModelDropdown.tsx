"use client";

import { useState, useRef, useEffect } from "react";
import { MODELS } from "@/constants/models";

type ModelDropdownProps = {
  selectedModel: string;
  onSelect:      (id: string) => void;
};

export function ModelDropdown({ selectedModel, onSelect }: ModelDropdownProps) {
  const [open, setOpen] = useState(false);
  const ref             = useRef<HTMLDivElement>(null);
  const current         = MODELS.find((m) => m.id === selectedModel) ?? MODELS[0];

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg hover:bg-gray-100 transition-colors"
      >
        <span className="text-base font-semibold text-gray-900">{current.label}</span>
        <svg viewBox="0 0 24 24" fill="none" className="w-3.5 h-3.5 text-gray-400" stroke="currentColor" strokeWidth="2.5">
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {open && (
        <div className="absolute left-0 top-full mt-1 w-44 bg-white border border-gray-200 rounded-xl shadow-lg py-1 z-50">
          {MODELS.map((m) => (
            <button
              key={m.id}
              onClick={() => { onSelect(m.id); setOpen(false); }}
              className={`w-full flex items-center justify-between px-3 py-2 text-sm text-left hover:bg-gray-50 transition-colors ${
                m.id === selectedModel ? "text-gray-900 font-medium" : "text-gray-600"
              }`}
            >
              {m.label}
              {m.id === selectedModel && (
                <svg viewBox="0 0 24 24" fill="none" className="w-3.5 h-3.5 text-gray-900" stroke="currentColor" strokeWidth="2.5">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
