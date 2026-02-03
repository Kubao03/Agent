// app/page.tsx
"use client"; // 声明这是一个在浏览器跑的“客户端组件”，因为我们要处理点击和输入

import { useState } from "react";

export default function ChatPage() {
  const [input, setInput] = useState(""); // 存储你输入的内容
  const [chatLog, setChatLog] = useState(""); // 存储后端回传的内容

  const handleSend = async () => {
  const response = await fetch("http://localhost:8000/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: input }), // 把输入的内容打包
  });
  
  const data = await response.json();
  setChatLog(data.reply); // 把后端的 reply 显示在屏幕上
};

  return (
    <div className="p-10 flex flex-col gap-4 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-blue-600">我的第一个 Agent 前端</h1>
      
      <div className="border p-4 h-64 bg-gray-50 rounded">
        <p className="text-gray-600">AI 回复：</p>
        <div className="mt-2 p-2 bg-white border rounded">{chatLog}</div>
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