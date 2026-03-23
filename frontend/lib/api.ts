import type { Message, Thread } from "@/types/chat";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function getThreads(): Promise<Thread[]> {
  const res = await fetch(`${API_URL}/api/threads`);
  if (!res.ok) throw new Error("Failed to fetch threads");
  return res.json();
}

export async function getThreadMessages(threadId: string): Promise<Message[]> {
  const res = await fetch(`${API_URL}/api/threads/${threadId}/messages`);
  if (!res.ok) throw new Error("Failed to fetch messages");
  return res.json();
}

export async function deleteThread(threadId: string): Promise<void> {
  await fetch(`${API_URL}/api/threads/${threadId}`, { method: "DELETE" });
}

export async function uploadFile(
  threadId: string,
  file: File,
  onProgress?: (status: "processing" | "done" | "error") => void,
): Promise<{ filename?: string; error?: string }> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("thread_id", threadId);
  const res = await fetch(`${API_URL}/api/upload`, { method: "POST", body: formData });
  const data = await res.json();

  if (data.status === "processing") {
    onProgress?.("processing");
    // 轮询直到处理完成
    while (true) {
      await new Promise((r) => setTimeout(r, 1500));
      const poll = await fetch(`${API_URL}/api/upload/status/${threadId}`);
      const s = await poll.json();
      if (s.status === "done") { onProgress?.("done"); return { filename: s.filename }; }
      if (s.status === "error") { onProgress?.("error"); return { error: s.error }; }
    }
  }

  return data;
}

export type StreamChatParams = {
  threadId:     string;
  message:      string;
  model:        string;
  uploadedFile?: string;
  signal:       AbortSignal;
};

export async function streamChat(params: StreamChatParams): Promise<Response> {
  return fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      thread_id:     params.threadId,
      message:       params.message,
      model:         params.model,
      uploaded_file: params.uploadedFile,
    }),
    signal: params.signal,
  });
}
