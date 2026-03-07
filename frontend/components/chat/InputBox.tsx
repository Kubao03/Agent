"use client";

import { useRef } from "react";

export type InputBoxProps = {
  input:         string;
  isStreaming:   boolean;
  setInput:      (v: string) => void;
  handleSend:    () => void;
  onAbort:       () => void;
  uploadedFile?: string;
  onUpload:      (file: File) => void;
};

export function InputBox({
  input, isStreaming, setInput, handleSend, onAbort, uploadedFile, onUpload,
}: InputBoxProps) {
  const fileRef = useRef<HTMLInputElement>(null);

  return (
    <div className="flex flex-col gap-2">
      {uploadedFile && (
        <div className="flex items-center gap-1.5 text-xs text-green-600 bg-green-50 border border-green-200 rounded-lg px-3 py-1.5 w-fit">
          <svg viewBox="0 0 24 24" fill="none" className="w-3.5 h-3.5" stroke="currentColor" strokeWidth="2">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
          {uploadedFile}
        </div>
      )}

      <div className="relative flex items-end">
        <input
          ref={fileRef}
          type="file"
          accept=".pdf"
          className="hidden"
          onChange={(e) => { if (e.target.files?.[0]) onUpload(e.target.files[0]); }}
        />

        <button
          onClick={() => fileRef.current?.click()}
          className="absolute left-2.5 bottom-2.5 w-8 h-8 flex items-center justify-center text-gray-400 hover:text-gray-600 transition-colors"
          title="上传 PDF"
        >
          <svg viewBox="0 0 24 24" fill="none" className="w-4 h-4" stroke="currentColor" strokeWidth="2">
            <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" />
          </svg>
        </button>

        <textarea
          rows={1}
          className="w-full pl-12 pr-12 py-3.5 bg-white border border-gray-200 rounded-2xl focus:ring-2 focus:ring-gray-300/50 focus:border-gray-400 transition-all outline-none text-gray-800 placeholder-gray-400 resize-none hover:border-gray-300 min-h-[52px] text-sm"
          value={input}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault();
              handleSend();
            }
          }}
          onChange={(e) => setInput(e.target.value)}
          placeholder="给 Agent 发送消息..."
        />

        {isStreaming ? (
          <button
            onClick={onAbort}
            className="absolute right-2.5 bottom-2.5 w-8 h-8 flex items-center justify-center bg-gray-900 text-white rounded-lg hover:bg-gray-700 active:scale-95 transition-all"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" className="w-3.5 h-3.5">
              <rect x="5" y="5" width="14" height="14" rx="1" />
            </svg>
          </button>
        ) : (
          <button
            onClick={handleSend}
            disabled={!input.trim()}
            className="absolute right-2.5 bottom-2.5 w-8 h-8 flex items-center justify-center bg-gray-900 text-white rounded-lg hover:bg-gray-700 active:scale-95 disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed transition-all"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}
