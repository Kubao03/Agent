// app/page.tsx
"use client"; // 声明这是一个在浏览器跑的“客户端组件”，因为我们要处理点击和输入

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneLight } from "react-syntax-highlighter/dist/esm/styles/prism";

export default function ChatPage() {
  const [input, setInput] = useState(""); // 存储你输入的内容
  const [chatLog, setChatLog] = useState(""); // 存储后端回传的内容

  const handleSend = async () => {
  if (!input.trim()) return;
  setChatLog(""); // 先清空上次的回复
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const response = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: input }), // 把输入的内容打包
  });
  if (!response.body) return;
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let done = false;
  let accumulatedResponse = "";

  while (!done) {
    const { value, done: doneReading } = await reader.read();
    done = doneReading;
    if (value) {
      const chunkValue = decoder.decode(value);
      accumulatedResponse += chunkValue;
      setChatLog(accumulatedResponse); // 实时更新聊天记录
    }
  }
};

  return (
    <div className="p-8 md:p-10 flex flex-col gap-6 max-w-4xl mx-auto min-h-screen">
      <h1 className="text-3xl md:text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
        我的第一个 Agent 前端
      </h1>
      
      <div className="border p-4 min-h-[400px] max-h-[600px] bg-gray-50 rounded overflow-y-auto">
        <p className="text-gray-600">AI 回复：</p>
        <div className="prose prose-blue max-w-none bg-white p-4 border rounded shadow-sm
                prose-pre:bg-transparent prose-pre:p-0 prose-pre:m-0 prose-pre:shadow-none">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              code({ node, inline, className, children, ...props }: any) {
                const match = /language-(\w+)/.exec(className || "");
                return !inline && match ? (
                  <SyntaxHighlighter
                    style={oneLight}
                    language={match[1]}
                    PreTag="div"
                    customStyle={{
                      margin: 0,
                      padding: '1.5rem',
                      backgroundColor: '#f8f9fa',
                      fontSize: '0.9rem',
                      borderRadius: '0.5rem',
                      border: 'none',
                    }}  
                    {...props}
                  >
                    {String(children).replace(/\n$/, "")}
                  </SyntaxHighlighter>
                ) : (
                  <code className={className} {...props}>
                    {children}
                  </code>
                );
              },
            }}
          >
            {chatLog}
          </ReactMarkdown>
        </div>
      </div>

      <div className="flex gap-2">
        <input 
          type="text" 
          className="border flex-1 p-2 rounded text-black" 
          value={input}
          onChange={(e) => setInput(e.target.value)} // 监听输入
          placeholder="输入消息..."
        />
        <button 
          onClick={handleSend}
          className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
        >
          发送
        </button>
      </div>
    </div>
  );
}