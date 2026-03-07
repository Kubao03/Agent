"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import type { Message, Thread } from "@/types/chat";
import { MODELS } from "@/constants/models";
import * as api from "@/lib/api";
import { parseSSEEvent } from "@/lib/sse";

export function useChat() {
  const [input, setInput]                             = useState("");
  const [messages, setMessages]                       = useState<Message[]>([]);
  const [isStreaming, setIsStreaming]                 = useState(false);
  const [uploadedFile, setUploadedFile]               = useState<string | undefined>();
  const [threads, setThreads]                         = useState<Thread[]>([]);
  const [activeThreadId, setActiveThreadId]           = useState(() => crypto.randomUUID());
  const [sidebarCollapsed, setSidebarCollapsed]       = useState(false);
  const [selectedModel, setSelectedModel]             = useState(MODELS[0].id);
  const bottomRef                                     = useRef<HTMLDivElement>(null);
  const abortControllerRef                            = useRef<AbortController | null>(null);

  const refreshThreads = useCallback(async () => {
    try {
      setThreads(await api.getThreads());
    } catch {
      // silently ignore — sidebar is non-critical
    }
  }, []);

  useEffect(() => { refreshThreads(); }, [refreshThreads]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleNew = useCallback(() => {
    setActiveThreadId(crypto.randomUUID());
    setMessages([]);
    setUploadedFile(undefined);
  }, []);

  const handleSelect = useCallback(async (id: string) => {
    setActiveThreadId(id);
    setUploadedFile(undefined);
    setMessages([]);
    try {
      const msgs = await api.getThreadMessages(id);
      setMessages(msgs);
      // 从历史消息里恢复最后一次上传的文件名
      const lastUpload = [...msgs].reverse().find((m) => m.uploadedFile)?.uploadedFile;
      if (lastUpload) setUploadedFile(lastUpload);
    } catch {
      // silently ignore
    }
  }, []);

  const handleDelete = useCallback(async (id: string) => {
    await api.deleteThread(id);
    if (id === activeThreadId) handleNew();
    setThreads((prev) => prev.filter((t) => t.id !== id));
  }, [activeThreadId, handleNew]);

  const handleUpload = useCallback(async (file: File) => {
    const data = await api.uploadFile(activeThreadId, file);
    if (!data.error) setUploadedFile(data.filename);
  }, [activeThreadId]);

  const handleAbort = useCallback(() => {
    abortControllerRef.current?.abort();
  }, []);

  const handleSend = useCallback(async () => {
    if (!input.trim() || isStreaming) return;

    const userMessage: Message = { role: "user", content: input.trim() };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsStreaming(true);
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const response = await api.streamChat({
        threadId:     activeThreadId,
        message:      userMessage.content,
        model:        selectedModel,
        uploadedFile,
        signal:       controller.signal,
      });

      if (!response.body) return;

      const reader  = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer    = "";
      let isDone    = false;

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
          if (!ev) continue;

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
              const last  = { ...updated[updated.length - 1] };
              const steps = [...(last.steps ?? [])];
              if (steps.length > 0) {
                steps[steps.length - 1] = { ...steps[steps.length - 1], snippet: ev.snippet, done: true };
              }
              last.steps = steps;
              updated[updated.length - 1] = last;
              return updated;
            });
          }
        }
      }

      refreshThreads();
    } catch (e: unknown) {
      if ((e as Error)?.name !== "AbortError") console.error(e);
    } finally {
      setIsStreaming(false);
      abortControllerRef.current = null;
    }
  }, [input, isStreaming, activeThreadId, selectedModel, uploadedFile, refreshThreads]);

  return {
    input,           setInput,
    messages,
    isStreaming,
    uploadedFile,
    threads,
    activeThreadId,
    sidebarCollapsed, setSidebarCollapsed,
    selectedModel,   setSelectedModel,
    bottomRef,
    handleNew,
    handleSelect,
    handleDelete,
    handleUpload,
    handleAbort,
    handleSend,
  };
}
