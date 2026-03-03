"use client";

import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneLight } from "react-syntax-highlighter/dist/esm/styles/prism";

type Message = {
  role: "user" | "assistant";
  content: string;
};

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

    if (!response.body) return;
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

  const hasConversation = messages.length > 0;

  return (
    <div className="flex flex-col h-screen bg-white text-gray-800">
      <header className="py-3.5 px-4 border-b border-gray-100/50 flex justify-center sticky top-0 bg-white/95 backdrop-blur-sm z-10">
        <div className="text-sm font-medium text-gray-600 tracking-wide">DeepSeek-R1 (Agent)</div>
      </header>

      <main className={`flex-1 overflow-y-auto overflow-x-hidden ${!hasConversation ? "flex items-center justify-center" : ""}`}>
        {!hasConversation ? (
          <div className="w-full max-w-3xl mx-auto px-4">
            <div className="text-center mb-8">
              <div className="w-20 h-20 bg-gradient-to-br from-blue-500 via-indigo-500 to-purple-600 rounded-3xl flex items-center justify-center mx-auto mb-6 shadow-xl relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-br from-white/20 to-transparent"></div>
                <svg viewBox="0 0 24 24" fill="none" className="w-12 h-12 text-white relative z-10">
                  <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <h1 className="text-3xl font-semibold text-gray-900 mb-2">你好，我是 AI Agent</h1>
              <p className="text-gray-500 text-lg">我可以帮助你解答问题、编写代码、分析数据等</p>
            </div>
            <div className="max-w-2xl mx-auto">
              <div className="relative flex items-end">
                <textarea
                  rows={1}
                  className="w-full pl-4 pr-12 py-3.5 bg-white border border-gray-200 rounded-2xl focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all outline-none text-gray-800 placeholder-gray-400 resize-none shadow-sm hover:border-gray-300 min-h-[52px]"
                  value={input}
                  onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="给 Agent 发送消息..."
                />
                <button
                  onClick={handleSend}
                  disabled={!input.trim() || isStreaming}
                  className="absolute right-2.5 bottom-2.5 w-8 h-8 flex items-center justify-center bg-gray-900 text-white rounded-lg hover:bg-gray-800 active:scale-95 disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed transition-all"
                >
                  <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                    <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                  </svg>
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto px-4 py-8 space-y-8">
            {messages.map((msg, index) => (
              <div key={index}>
                {msg.role === "user" ? (
                  <div className="flex justify-end">
                    <div className="bg-blue-400 text-white px-4 py-2.5 rounded-2xl max-w-[80%] text-sm leading-relaxed shadow-sm hover:bg-blue-500 transition-colors">
                      {msg.content}
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col gap-4">
                    <div className="prose prose-slate prose-lg max-w-none
                          prose-headings:font-semibold prose-headings:text-gray-900 prose-headings:mt-6 prose-headings:mb-3
                          prose-p:text-gray-700 prose-p:leading-7 prose-p:my-4
                          prose-strong:text-gray-900 prose-strong:font-semibold
                          prose-code:text-pink-600 prose-code:bg-pink-50 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:font-mono prose-code:text-sm prose-code:before:content-[''] prose-code:after:content-['']
                          prose-pre:bg-gray-50 prose-pre:border prose-pre:border-gray-200
                          prose-pre:p-4 prose-pre:m-0 prose-pre:shadow-sm prose-pre:rounded-lg
                          prose-ul:my-4 prose-ol:my-4
                          prose-li:my-2 prose-li:leading-7
                          prose-blockquote:border-l-4 prose-blockquote:border-gray-300 prose-blockquote:pl-4 prose-blockquote:italic prose-blockquote:text-gray-600">
                      {msg.content ? (
                        <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
                          code({ node, inline, className, children, ...props }: any) {
                            const match = /language-(\w+)/.exec(className || "");
                            return !inline && match ? (
                              <SyntaxHighlighter style={oneLight} language={match[1]} PreTag="div"
                                customStyle={{ margin: 0, padding: "1rem", backgroundColor: "#f8fafc", fontSize: "0.875rem", borderRadius: "0.5rem", border: "none" }}
                                {...props}>
                                {String(children).replace(/\n$/, "")}
                              </SyntaxHighlighter>
                            ) : (
                              <code className="bg-pink-50 text-pink-600 px-1.5 py-0.5 rounded text-sm font-mono" {...props}>{children}</code>
                            );
                          }
                        }}>
                          {msg.content}
                        </ReactMarkdown>
                      ) : (
                        <span className="inline-block w-2 h-5 bg-gray-400 animate-pulse rounded" />
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </main>

      {hasConversation && (
        <footer className="p-4 md:pb-8 border-t border-gray-100">
          <div className="max-w-3xl mx-auto">
            <div className="relative flex items-end">
              <textarea
                rows={1}
                className="w-full pl-4 pr-12 py-3.5 bg-white border border-gray-200 rounded-2xl focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all outline-none text-gray-800 placeholder-gray-400 resize-none shadow-sm hover:border-gray-300 min-h-[52px]"
                value={input}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                onChange={(e) => setInput(e.target.value)}
                placeholder="给 Agent 发送消息..."
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || isStreaming}
                className="absolute right-2.5 bottom-2.5 w-8 h-8 flex items-center justify-center bg-gray-900 text-white rounded-lg hover:bg-gray-800 active:scale-95 disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed transition-all"
              >
                <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                  <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                </svg>
              </button>
            </div>
            <p className="text-xs text-gray-400 text-center mt-4">
              Agent 可能会产生错误信息，请核实重要内容。
            </p>
          </div>
        </footer>
      )}
    </div>
  );
}
