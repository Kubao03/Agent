"use client";

import { useChat } from "@/hooks/useChat";
import { Sidebar } from "@/components/sidebar/Sidebar";
import { AssistantMessage } from "@/components/chat/AssistantMessage";
import { InputBox } from "@/components/chat/InputBox";
import { ModelDropdown } from "@/components/ui/ModelDropdown";

export default function ChatPage() {
  const {
    input, setInput,
    messages,
    isStreaming,
    uploadedFile,
    threads,
    activeThreadId,
    sidebarCollapsed, setSidebarCollapsed,
    selectedModel,   setSelectedModel,
    bottomRef,
    handleNew, handleSelect, handleDelete,
    handleUpload, handleAbort, handleSend,
  } = useChat();

  const inputBoxProps = {
    input, isStreaming, setInput, handleSend,
    onAbort: handleAbort, uploadedFile, onUpload: handleUpload,
  };
  const hasConversation = messages.length > 0;

  return (
    <div className="flex h-screen bg-white text-gray-800 overflow-hidden">
      <Sidebar
        threads={threads}
        activeId={activeThreadId}
        onSelect={handleSelect}
        onNew={handleNew}
        onDelete={handleDelete}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed((v) => !v)}
      />

      <div className="flex flex-col flex-1 min-w-0">
        <header className="py-2.5 px-4 flex items-center sticky top-0 bg-white z-10">
          <ModelDropdown selectedModel={selectedModel} onSelect={setSelectedModel} />
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
          <footer className="px-4 py-4 md:pb-6 bg-white">
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
