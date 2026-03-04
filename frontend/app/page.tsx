"use client";

import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneLight } from "react-syntax-highlighter/dist/esm/styles/prism";

// ─── Types ────────────────────────────────────────────────────────────────────

type Message = {
  role: "user" | "assistant";
  content: string;
};

type InputBoxProps = {
  input: string;
  isStreaming: boolean;
  setInput: (v: string) => void;
  handleSend: () => void;
};

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

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-xl overflow-hidden my-4 border border-gray-200 bg-gray-50">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-200">
        <div className="flex items-center gap-2 text-gray-500">
          <svg viewBox="0 0 24 24" fill="none" className="w-3.5 h-3.5" stroke="currentColor" strokeWidth="2">
            <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
          </svg>
          <span className="text-xs font-medium">{language}</span>
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-700 transition-colors"
        >
          {copied ? <><CheckIcon />Copied!</> : <><CopyIcon />Copy</>}
        </button>
      </div>
      <SyntaxHighlighter
        style={oneLight}
        language={language}
        PreTag="div"
        customStyle={{ margin: 0, padding: "1rem", background: "#f9fafb", fontSize: "0.8125rem", lineHeight: "1.6", borderRadius: 0 }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}

function AssistantMessage({ content }: { content: string }) {
  if (!content) {
    return <span className="inline-block w-2 h-5 bg-gray-400 animate-pulse rounded" />;
  }
  return (
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
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ node, inline, className, children, ...props }: any) {
            const match = /language-(\w+)/.exec(className || "");
            const code = String(children).replace(/\n$/, "");
            return !inline && match ? (
              <CodeBlock language={match[1]} code={code} />
            ) : (
              <code className="text-[#e06c75] bg-gray-100 px-1.5 py-0.5 rounded text-sm font-mono" {...props}>
                {children}
              </code>
            );
          },
          pre({ children }) {
            return <>{children}</>;
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

function InputBox({ input, isStreaming, setInput, handleSend }: InputBoxProps) {
  return (
    <div className="relative flex items-end">
      <textarea
        rows={1}
        className="w-full pl-4 pr-12 py-3.5 bg-white border border-gray-200 rounded-2xl focus:ring-2 focus:ring-gray-300/50 focus:border-gray-400 transition-all outline-none text-gray-800 placeholder-gray-400 resize-none hover:border-gray-300 min-h-[52px] text-sm"
        value={input}
        onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
        onChange={(e) => setInput(e.target.value)}
        placeholder="给 Agent 发送消息..."
      />
      <button
        onClick={handleSend}
        disabled={!input.trim() || isStreaming}
        className="absolute right-2.5 bottom-2.5 w-8 h-8 flex items-center justify-center bg-gray-900 text-white rounded-lg hover:bg-gray-700 active:scale-95 disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed transition-all"
      >
        <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
          <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
        </svg>
      </button>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ChatPage() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return;

    const userMessage: Message = { role: "user", content: input.trim() };
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setInput("");
    setIsStreaming(true);
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const response = await fetch(`${API_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: updatedMessages }),
    });

    if (!response.body) { setIsStreaming(false); return; }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let done = false;

    while (!done) {
      const { value, done: doneReading } = await reader.read();
      done = doneReading;
      if (value) {
        const chunk = decoder.decode(value);
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: "assistant",
            content: updated[updated.length - 1].content + chunk,
          };
          return updated;
        });
      }
    }

    setIsStreaming(false);
  };

  const inputBoxProps = { input, isStreaming, setInput, handleSend };
  const hasConversation = messages.length > 0;

  return (
    <div className="flex flex-col h-screen bg-white text-gray-800">
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
                  <AssistantMessage content={msg.content} />
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
  );
}
