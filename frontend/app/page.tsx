"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneLight } from "react-syntax-highlighter/dist/esm/styles/prism";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ─── SSE event types ──────────────────────────────────────────────────────────

type TextEvent      = { type: "text";       content: string };
type ToolStartEvent = { type: "tool_start"; tool: string; query: string };
type ToolEndEvent   = { type: "tool_end";   snippet: string };
type SSEEvent = TextEvent | ToolStartEvent | ToolEndEvent;

function parseSSEEvent(raw: string): SSEEvent | null {
  try {
    const ev = JSON.parse(raw) as SSEEvent;
    if (ev.type === "text" || ev.type === "tool_start" || ev.type === "tool_end") return ev;
  } catch { /* ignore */ }
  return null;
}

// ─── Types ────────────────────────────────────────────────────────────────────

type Step = { tool: string; query: string; snippet?: string; done: boolean };
type Message = { role: "user" | "assistant"; content: string; steps?: Step[] };
type Thread = { id: string; title: string; created_at: string };

// ─── Sub-components ───────────────────────────────────────────────────────────

function CopyIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="w-3.5 h-3.5" stroke="currentColor" strokeWidth="2">
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
      <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="w-3.5 h-3.5" stroke="currentColor" strokeWidth="2.5">
      <polyline points="20 6 9 17 4 12"/>
    </svg>
  );
}

function CodeBlock({ language, code }: { language: string; code: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => { navigator.clipboard.writeText(code); setCopied(true); setTimeout(() => setCopied(false), 2000); };
  return (
    <div className="rounded-xl overflow-hidden my-4 border border-gray-200 bg-gray-50">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-200">
        <div className="flex items-center gap-2 text-gray-500">
          <svg viewBox="0 0 24 24" fill="none" className="w-3.5 h-3.5" stroke="currentColor" strokeWidth="2">
            <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
          </svg>
          <span className="text-xs font-medium">{language}</span>
        </div>
        <button onClick={handleCopy} className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-700 transition-colors">
          {copied ? <><CheckIcon />Copied!</> : <><CopyIcon />Copy</>}
        </button>
      </div>
      <SyntaxHighlighter style={oneLight} language={language} PreTag="div"
        customStyle={{ margin: 0, padding: "1rem", background: "#f9fafb", fontSize: "0.8125rem", lineHeight: "1.6", borderRadius: 0 }}>
        {code}
      </SyntaxHighlighter>
    </div>
  );
}

function ThinkingPanel({ steps, isStreaming }: { steps: Step[]; isStreaming: boolean }) {
  const [open, setOpen] = useState(true);
  if (steps.length === 0) return null;
  const allDone = steps.every((s) => s.done);
  return (
    <div className="mb-4 rounded-xl border border-gray-200 bg-gray-50 text-sm overflow-hidden">
      <button onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-4 py-2.5 text-gray-500 hover:text-gray-700 transition-colors">
        <span className="flex items-center gap-2 font-medium">
          {isStreaming && !allDone ? (
            <span className="inline-flex gap-0.5">
              <span className="w-1 h-1 rounded-full bg-gray-400 animate-bounce [animation-delay:0ms]" />
              <span className="w-1 h-1 rounded-full bg-gray-400 animate-bounce [animation-delay:150ms]" />
              <span className="w-1 h-1 rounded-full bg-gray-400 animate-bounce [animation-delay:300ms]" />
            </span>
          ) : <span>✓</span>}
          思考过程
        </span>
        <span className="text-xs text-gray-400">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="border-t border-gray-200 divide-y divide-gray-100">
          {steps.map((step, i) => (
            <div key={i} className="px-4 py-3 flex flex-col gap-1">
              <div className="flex items-center gap-2 text-gray-600">
                {step.done ? <span className="text-green-500">✓</span> :
                  <span className="inline-block w-3 h-3 rounded-full border-2 border-gray-400 border-t-transparent animate-spin" />}
                <span>🔍 搜索：<span className="font-medium text-gray-800">{step.query}</span></span>
              </div>
              {step.snippet && <p className="ml-6 text-xs text-gray-400 line-clamp-2">{step.snippet}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function AssistantMessage({ content, steps, isStreaming }: { content: string; steps?: Step[]; isStreaming?: boolean }) {
  return (
    <div>
      <ThinkingPanel steps={steps ?? []} isStreaming={!!isStreaming} />
      {!content && <span className="inline-block w-2 h-5 bg-gray-400 animate-pulse rounded" />}
      {content && (
        <div className="prose prose-sm max-w-none
            prose-p:text-gray-900 prose-p:leading-7 prose-p:my-3 prose-p:text-[15px]
            prose-headings:font-semibold prose-headings:text-gray-900 prose-headings:mt-5 prose-headings:mb-2
            prose-strong:text-gray-900 prose-strong:font-semibold
            prose-ul:my-3 prose-ol:my-3 prose-li:my-1 prose-li:text-gray-900 prose-li:text-[15px]
            prose-code:text-[#e06c75] prose-code:bg-gray-100 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-code:font-mono prose-code:before:content-[''] prose-code:after:content-['']
            prose-pre:p-0 prose-pre:bg-transparent prose-pre:my-0 prose-pre:border-none
            prose-blockquote:border-l-4 prose-blockquote:border-gray-300 prose-blockquote:pl-4 prose-blockquote:text-gray-600 prose-blockquote:italic
            prose-hr:border-gray-200
            prose-table:text-sm prose-th:text-gray-900 prose-td:text-gray-700">
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
            code({ node, inline, className, children, ...props }: any) {
              const match = /language-(\w+)/.exec(className || "");
              const code = String(children).replace(/\n$/, "");
              return !inline && match ? <CodeBlock language={match[1]} code={code} /> : (
                <code className="text-[#e06c75] bg-gray-100 px-1.5 py-0.5 rounded text-sm font-mono" {...props}>{children}</code>
              );
            },
            pre({ children }) { return <>{children}</>; },
          }}>
            {content}
          </ReactMarkdown>
        </div>
      )}
    </div>
  );
}

type InputBoxProps = {
  input: string; isStreaming: boolean;
  setInput: (v: string) => void; handleSend: () => void;
  uploadedFile?: string; onUpload: (file: File) => void;
};

function InputBox({ input, isStreaming, setInput, handleSend, uploadedFile, onUpload }: InputBoxProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  return (
    <div className="flex flex-col gap-2">
      {uploadedFile && (
        <div className="flex items-center gap-1.5 text-xs text-green-600 bg-green-50 border border-green-200 rounded-lg px-3 py-1.5 w-fit">
          <svg viewBox="0 0 24 24" fill="none" className="w-3.5 h-3.5" stroke="currentColor" strokeWidth="2">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/>
          </svg>
          {uploadedFile}
        </div>
      )}
      <div className="relative flex items-end">
        <input ref={fileRef} type="file" accept=".pdf" className="hidden"
          onChange={(e) => { if (e.target.files?.[0]) onUpload(e.target.files[0]); }} />
        <button onClick={() => fileRef.current?.click()}
          className="absolute left-2.5 bottom-2.5 w-8 h-8 flex items-center justify-center text-gray-400 hover:text-gray-600 transition-colors"
          title="上传 PDF">
          <svg viewBox="0 0 24 24" fill="none" className="w-4 h-4" stroke="currentColor" strokeWidth="2">
            <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/>
          </svg>
        </button>
        <textarea rows={1}
          className="w-full pl-12 pr-12 py-3.5 bg-white border border-gray-200 rounded-2xl focus:ring-2 focus:ring-gray-300/50 focus:border-gray-400 transition-all outline-none text-gray-800 placeholder-gray-400 resize-none hover:border-gray-300 min-h-[52px] text-sm"
          value={input}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
          onChange={(e) => setInput(e.target.value)}
          placeholder="给 Agent 发送消息..."
        />
        <button onClick={handleSend} disabled={!input.trim() || isStreaming}
          className="absolute right-2.5 bottom-2.5 w-8 h-8 flex items-center justify-center bg-gray-900 text-white rounded-lg hover:bg-gray-700 active:scale-95 disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed transition-all">
          <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
        </button>
      </div>
    </div>
  );
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────

function Sidebar({
  threads, activeId, onSelect, onNew, onDelete,
}: {
  threads: Thread[];
  activeId: string;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
}) {
  return (
    <aside className="w-60 shrink-0 flex flex-col border-r border-gray-200 bg-gray-50 h-screen">
      <div className="p-3 border-b border-gray-200">
        <button onClick={onNew}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-200 rounded-lg hover:bg-gray-100 transition-colors">
          <svg viewBox="0 0 24 24" fill="none" className="w-4 h-4" stroke="currentColor" strokeWidth="2">
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          新建对话
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto p-2 space-y-0.5">
        {threads.length === 0 && (
          <p className="text-xs text-gray-400 text-center mt-6">暂无对话记录</p>
        )}
        {threads.map((t) => (
          <div key={t.id}
            className={`group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-colors ${
              t.id === activeId ? "bg-white shadow-sm text-gray-900" : "text-gray-600 hover:bg-white hover:text-gray-900"
            }`}
            onClick={() => onSelect(t.id)}>
            <svg viewBox="0 0 24 24" fill="none" className="w-3.5 h-3.5 shrink-0 text-gray-400" stroke="currentColor" strokeWidth="2">
              <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
            </svg>
            <span className="flex-1 text-xs truncate">{t.title}</span>
            <button
              onClick={(e) => { e.stopPropagation(); onDelete(t.id); }}
              className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 transition-all p-0.5 rounded"
              title="删除">
              <svg viewBox="0 0 24 24" fill="none" className="w-3 h-3" stroke="currentColor" strokeWidth="2">
                <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/>
              </svg>
            </button>
          </div>
        ))}
      </nav>
    </aside>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ChatPage() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<string>();
  const [threads, setThreads] = useState<Thread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState(() => crypto.randomUUID());
  const bottomRef = useRef<HTMLDivElement>(null);

  const fetchThreads = useCallback(async () => {
    const res = await fetch(`${API_URL}/api/threads`);
    if (res.ok) setThreads(await res.json());
  }, []);

  useEffect(() => { fetchThreads(); }, [fetchThreads]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleNew = () => {
    setActiveThreadId(crypto.randomUUID());
    setMessages([]);
    setUploadedFile(undefined);
  };

  const handleSelect = async (id: string) => {
    setActiveThreadId(id);
    setUploadedFile(undefined);
    setMessages([]);
    const res = await fetch(`${API_URL}/api/threads/${id}/messages`);
    if (res.ok) setMessages(await res.json());
  };

  const handleDelete = async (id: string) => {
    await fetch(`${API_URL}/api/threads/${id}`, { method: "DELETE" });
    if (id === activeThreadId) handleNew();
    setThreads((prev) => prev.filter((t) => t.id !== id));
  };

  const handleUpload = async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("thread_id", activeThreadId);
    const res = await fetch(`${API_URL}/api/upload`, { method: "POST", body: formData });
    const data = await res.json();
    if (!data.error) setUploadedFile(data.filename);
  };

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return;

    const userMessage: Message = { role: "user", content: input.trim() };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsStreaming(true);
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    const response = await fetch(`${API_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ thread_id: activeThreadId, message: userMessage.content }),
    });

    if (!response.body) { setIsStreaming(false); return; }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let isDone = false;

    while (!isDone) {
      const { value, done: readerDone } = await reader.read();
      if (readerDone) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const raw = line.slice(6).trim();
        if (raw === "[DONE]") { isDone = true; break; }
        const ev = parseSSEEvent(raw);
        if (ev) {
          if (ev.type === "text") {
            setMessages((prev) => {
              const updated = [...prev];
              const last = { ...updated[updated.length - 1] };
              last.content += ev.content;
              updated[updated.length - 1] = last;
              return updated;
            });
          } else if (ev.type === "tool_start") {
            setMessages((prev) => {
              const updated = [...prev];
              const last = { ...updated[updated.length - 1] };
              last.steps = [...(last.steps ?? []), { tool: ev.tool, query: ev.query, done: false }];
              updated[updated.length - 1] = last;
              return updated;
            });
          } else if (ev.type === "tool_end") {
            setMessages((prev) => {
              const updated = [...prev];
              const last = { ...updated[updated.length - 1] };
              const steps = [...(last.steps ?? [])];
              if (steps.length > 0) steps[steps.length - 1] = { ...steps[steps.length - 1], snippet: ev.snippet, done: true };
              last.steps = steps;
              updated[updated.length - 1] = last;
              return updated;
            });
          }
        }
      }
    }

    setIsStreaming(false);
    fetchThreads();
  };

  const inputBoxProps = { input, isStreaming, setInput, handleSend, uploadedFile, onUpload: handleUpload };
  const hasConversation = messages.length > 0;

  return (
    <div className="flex h-screen bg-white text-gray-800 overflow-hidden">
      <Sidebar
        threads={threads}
        activeId={activeThreadId}
        onSelect={handleSelect}
        onNew={handleNew}
        onDelete={handleDelete}
      />

      <div className="flex flex-col flex-1 min-w-0">
        <header className="py-3 px-4 border-b border-gray-200 flex justify-center sticky top-0 bg-white z-10">
          <span className="text-sm font-medium text-gray-700">DeepSeek Agent</span>
        </header>

        <main className={`flex-1 overflow-y-auto overflow-x-hidden ${!hasConversation ? "flex items-center justify-center" : ""}`}>
          {!hasConversation ? (
            <div className="w-full max-w-3xl mx-auto px-4">
              <div className="text-center mb-8">
                <h1 className="text-2xl font-semibold text-gray-900 mb-2">有什么可以帮助你的？</h1>
              </div>
              <InputBox {...inputBoxProps} />
            </div>
          ) : (
            <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
              {messages.map((msg, index) => (
                <div key={index}>
                  {msg.role === "user" ? (
                    <div className="flex justify-end">
                      <div className="bg-blue-50 text-gray-900 px-4 py-3 rounded-2xl max-w-[75%] text-base leading-relaxed">
                        {msg.content}
                      </div>
                    </div>
                  ) : (
                    <AssistantMessage
                      content={msg.content}
                      steps={msg.steps}
                      isStreaming={isStreaming && index === messages.length - 1}
                    />
                  )}
                </div>
              ))}
              <div ref={bottomRef} />
            </div>
          )}
        </main>

        {hasConversation && (
          <footer className="px-4 py-4 md:pb-6 border-t border-gray-100 bg-white">
            <div className="max-w-3xl mx-auto">
              <InputBox {...inputBoxProps} />
              <p className="text-xs text-gray-400 text-center mt-3">AI 可能会出错，请核实重要信息。</p>
            </div>
          </footer>
        )}
      </div>
    </div>
  );
}
